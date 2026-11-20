"""Voice-cloned narration pipeline for OmniVoice (VoiceStudio's local TTS engine).

Splits a story file into scenes (blank-line separated), generates each scene
in your own cloned voice from a short reference recording, and concatenates
everything into one final narration file.

Usage:
    python narrate.py \
        --story examples/story.txt \
        --ref_audio my_voice.wav \
        --ref_text "레퍼런스 녹음의 정확한 대본." \
        --outdir output
"""

import argparse
import difflib
import json
import logging
import os
import re

import numpy as np
import soundfile as sf
import torch

from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.dtype import tts_dtype_name


def get_best_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_scenes(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return [s.strip() for s in text.split("\n\n") if s.strip()]


# A line "devil: 흐하하!" is read in the devil voice; the tag must name a voice
# (or alias) given with --voices, otherwise the line is ordinary text.
_TAG = re.compile(r"^\s*([^\s:：]{1,16})\s*[:：]\s*(.+)$")


def split_speakers(scene: str, known: dict[str, str], default: str) -> list[tuple[str, str]]:
    """[(voice, text), ...] for one scene; neighbouring lines of the same
    voice are joined so each voice reads its part in one go."""
    segments: list[tuple[str, str]] = []
    for line in scene.splitlines():
        line = line.strip()
        if not line:
            continue
        voice, text = default, line
        m = _TAG.match(line)
        if m and m.group(1).lower() in known:
            voice, text = known[m.group(1).lower()], m.group(2).strip()
        if segments and segments[-1][0] == voice:
            segments[-1] = (voice, segments[-1][1] + " " + text)
        else:
            segments.append((voice, text))
    return segments


_SENT = re.compile(r"(?<=[.!?…])\s+")


def _bare(text: str) -> str:
    return re.sub(r"[^\w]", "", text or "")


def match_hint(heard: str, hint: str, threshold: float = 0.9) -> tuple[str | None, float]:
    """The run of whole sentences in hint that reads like heard (the passage's
    own transcription), to fix its spelling. None if no run is close enough --
    then the heard words stay, since they are what the audio actually says."""
    sentences = [x.strip() for x in _SENT.split(hint.strip()) if x.strip()]
    target, best, best_ratio = _bare(heard), None, 0.0
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences) + 1):
            cand = " ".join(sentences[i:j])
            ratio = difflib.SequenceMatcher(None, target, _bare(cand)).ratio()
            if ratio > best_ratio:
                best, best_ratio = cand, ratio
    # Same length too: a spelling fix keeps the syllable count, while a stray
    # "습니다" at an edge adds syllables the known sentences don't have.
    if best is None or best_ratio < threshold or abs(len(_bare(best)) - len(target)) > 1:
        return None, best_ratio
    return best, best_ratio


def edge_extra(heard: str, expected: str) -> tuple[int, int]:
    """Syllables heard before / after the expected text (spaces and marks
    ignored): a stray "습니다" at a line's start or end shows up here."""
    h, x = _bare(heard), _bare(expected)
    blocks = [b for b in difflib.SequenceMatcher(None, h, x, autojunk=False).get_matching_blocks() if b.size]
    if not blocks:
        return len(h), 0
    first, last = blocks[0], blocks[-1]
    lead = max(0, first.a - first.b)
    trail = max(0, (len(h) - (last.a + last.size)) - (len(x) - (last.b + last.size)))
    return lead, trail


def silence_split(wav: np.ndarray, sr: int, min_gap: float = 0.2) -> list[int]:
    """Sample positions in the middle of each silence of at least min_gap."""
    frame = int(0.02 * sr)
    n = len(wav) // frame
    if n < 3:
        return []
    rms = np.sqrt(np.mean(wav[: n * frame].reshape(n, frame) ** 2, axis=1))
    quiet = rms < rms.max() * 0.02
    cuts, start = [], None
    for i in range(n + 1):
        q = i < n and quiet[i]
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * frame >= min_gap * sr and start > 0 and i < n:
                cuts.append((start + i) // 2 * frame)
            start = None
    return cuts


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--story", required=True, help="Text file; scenes separated by a blank line")
    p.add_argument("--ref_audio", default=None, help="Clean reference recording of your voice (wav)")
    p.add_argument(
        "--ref_text",
        default=None,
        help="Exact transcript of ref_audio, trimmed to the same 3-10s passage as the audio. "
        "Omit to let the engine auto-pick and transcribe the best short passage itself.",
    )
    p.add_argument("--language", default="Korean")
    p.add_argument("--outdir", default="output")
    p.add_argument("--model", default="k2-fsa/OmniVoice")
    p.add_argument("--num_step", type=int, default=32, help="Diffusion steps; higher = better quality, slower")
    p.add_argument("--guidance_scale", type=float, default=2.0)
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument(
        "--chunk_seconds",
        type=float,
        default=15.0,
        help="Split a long scene into pieces of about this many seconds; every piece re-reads "
        "the voice sample, so shorter pieces drift less from the real voice",
    )
    p.add_argument(
        "--chunk_threshold",
        type=float,
        default=30.0,
        help="Only split scenes estimated to be longer than this many seconds",
    )
    p.add_argument(
        "--voices",
        default=None,
        help='JSON: name -> [audio path, transcript or null, settings or null]. Overrides --ref_audio/--ref_text',
    )
    p.add_argument("--default_voice", default=None, help="Voice for untagged lines (default: first in --voices)")
    p.add_argument("--aliases", default=None, help='JSON: extra tag -> voice name, e.g. {"해설": "reviewer"}')
    p.add_argument("--retries", type=int, default=2, help="Re-make a line up to this many times when stray words are heard at its edges")
    p.add_argument("--segment_gap_seconds", type=float, default=0.3, help="Silence between speakers in one scene")
    p.add_argument("--gap_seconds", type=float, default=0.6, help="Silence inserted between scenes")
    return p


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    args = build_parser().parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    scenes = load_scenes(args.story)
    if not scenes:
        raise SystemExit(f"No scenes found in {args.story} (separate scenes with a blank line)")
    logging.info("%d scene(s) found in %s", len(scenes), args.story)

    device = get_best_device()
    logging.info("Loading OmniVoice (%s) on %s ...", args.model, device)
    model = OmniVoice.from_pretrained(
        args.model, device_map=device, dtype=getattr(torch, tts_dtype_name(device))
    )

    base = {
        "chunk_seconds": args.chunk_seconds,
        "chunk_threshold": args.chunk_threshold,
        "guidance_scale": args.guidance_scale,
        "num_step": args.num_step,
    }
    if args.voices:
        voices = {
            k: (v[0], v[1], {**base, **((v[2] if len(v) > 2 else None) or {})}, v[3] if len(v) > 3 else None)
            for k, v in json.loads(args.voices).items()
        }
    elif args.ref_audio:
        voices = {"main": (args.ref_audio, args.ref_text, base, None)}
    else:
        raise SystemExit("Give --voices or --ref_audio")
    default = args.default_voice if args.default_voice in voices else next(iter(voices))
    known = {k.lower(): k for k in voices}
    for tag, name in (json.loads(args.aliases) if args.aliases else {}).items():
        known[tag.lower()] = name if name in voices else default

    prompts: dict = {}

    def prompt_for(name: str):
        # One voice sample per voice, reused for every line it reads.
        if name in prompts:
            return prompts[name]
        audio, text, _, hint = voices[name]
        if text is not None:
            try:
                prompts[name] = model.create_voice_clone_prompt(ref_audio=audio, ref_text=text)
            except ValueError as exc:
                # A transcript only works for up to 20s of audio; use the whole clip instead.
                logging.warning("voice %s: transcript not usable (%s) -- auto-selecting a passage", name, exc)
                text = None
        if text is None:
            if getattr(model, "_asr_pipe", None) is None:
                # The library's implicit fallback refuses to download an ASR model, so load it explicitly.
                logging.info("loading ASR for automatic reference transcription ...")
                model.load_asr_model()
            prompts[name] = model.create_voice_clone_prompt(ref_audio=audio, ref_text=None)
            if hint:
                # The sample's words must match its audio exactly, or the clone
                # tacks the unmatched sounds onto its own lines. Keep what was
                # heard; only swap in the known wording when it is the same text.
                heard = prompts[name].ref_text
                fixed, ratio = match_hint(heard, hint)
                logging.info("voice %s heard: %s | hint match %.2f -> %s", name, heard, ratio, fixed or "(keep heard)")
                if fixed:
                    prompts[name] = model.create_voice_clone_prompt(ref_audio=audio, ref_text=fixed)
        p = prompts[name]
        logging.info(
            "voice sample %s: %s | %.1fs | transcript: %s",
            name, audio, p.ref_audio_tokens.shape[-1] / model.audio_tokenizer.config.frame_rate, p.ref_text,
        )
        return p

    stats = {"lines": 0, "flagged": 0, "still": 0}

    def make(name: str, text: str):
        cfg = voices[name][2]
        audios = model.generate(
            text=text,
            language=args.language,
            voice_clone_prompt=prompt_for(name),
            num_step=int(cfg["num_step"]),
            guidance_scale=float(cfg["guidance_scale"]),
            speed=args.speed,
            audio_chunk_duration=float(cfg["chunk_seconds"]),
            audio_chunk_threshold=float(cfg["chunk_threshold"]),
        )
        return audios[0]

    def speak(name: str, text: str) -> np.ndarray:
        """Make a line, listen to it, and re-make it if stray words (a sample's
        leftover "습니다") are heard before or after the expected text."""
        stats["lines"] += 1
        if getattr(model, "_asr_pipe", None) is None:
            model.load_asr_model()
        best, best_extra = None, None
        for attempt in range(args.retries + 1):
            audio = make(name, text)
            lead, trail = edge_extra(model.transcribe((audio.detach().cpu().float(), model.sampling_rate)), text)
            extra = lead + trail
            if best is None or extra < best_extra:
                best, best_extra = audio, extra
            if lead < 2 and trail < 2:
                break
            if attempt == 0:
                stats["flagged"] += 1
            logging.info("  %s: stray sound at the edges (before %d, after %d syllables) -- retry %d",
                         name, lead, trail, attempt + 1)
        wav = best.squeeze().detach().cpu().float().numpy()
        if best_extra is not None and best_extra >= 2:
            # Last resort: a stray word usually sits behind a short silence at
            # the very start or end -- drop that piece if the rest then reads right.
            cuts = silence_split(wav, model.sampling_rate)
            for lo, hi in ((cuts[0] if cuts else None, None), (None, cuts[-1] if cuts else None)):
                if lo is None and hi is None:
                    continue
                trial = wav[lo or 0: hi or len(wav)]
                heard = model.transcribe((torch.from_numpy(trial), model.sampling_rate))
                lead, trail = edge_extra(heard, text)
                missing = len(_bare(text)) - len(_bare(heard))
                if lead + trail < best_extra and missing <= 2:
                    logging.info("  %s: cut a stray piece at the %s", name, "start" if lo else "end")
                    wav, best_extra = trial, lead + trail
            if best_extra >= 2:
                stats["still"] += 1
        return wav

    gap = np.zeros(int(args.gap_seconds * model.sampling_rate), dtype=np.float32)
    seg_gap = np.zeros(int(args.segment_gap_seconds * model.sampling_rate), dtype=np.float32)
    pieces: list[np.ndarray] = []

    for i, scene in enumerate(scenes, 1):
        segments = split_speakers(scene, known, default)
        logging.info("[%d/%d] generating (%s): %s...", i, len(scenes), ", ".join(v for v, _ in segments), scene[:50])
        parts: list[np.ndarray] = []
        for j, (name, text) in enumerate(segments):
            if j:
                parts.append(seg_gap)
            parts.append(speak(name, text))
        wav = np.concatenate(parts)
        scene_path = os.path.join(args.outdir, f"scene_{i:02d}.wav")
        sf.write(scene_path, wav, model.sampling_rate)
        logging.info("  saved %s", scene_path)
        pieces.append(wav)
        if i != len(scenes):
            pieces.append(gap)

    logging.info("edge check: %d line(s), %d had stray sounds, %d still had them after retries",
                 stats["lines"], stats["flagged"], stats["still"])
    full = np.concatenate(pieces)
    full_path = os.path.join(args.outdir, "full_story.wav")
    sf.write(full_path, full, model.sampling_rate)
    logging.info("Done. Full narration: %s (%.1fs)", full_path, len(full) / model.sampling_rate)


if __name__ == "__main__":
    main()
