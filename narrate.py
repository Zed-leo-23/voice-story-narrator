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
        voices = {k: (v[0], v[1], {**base, **(v[2] or {})}) for k, v in json.loads(args.voices).items()}
    elif args.ref_audio:
        voices = {"main": (args.ref_audio, args.ref_text, base)}
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
        audio, text, _ = voices[name]
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
        p = prompts[name]
        logging.info(
            "voice sample %s: %s | %.1fs | transcript: %s",
            name, audio, p.ref_audio_tokens.shape[-1] / model.audio_tokenizer.config.frame_rate, p.ref_text,
        )
        return p

    def speak(name: str, text: str) -> np.ndarray:
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
        return audios[0].squeeze().detach().cpu().float().numpy()

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

    full = np.concatenate(pieces)
    full_path = os.path.join(args.outdir, "full_story.wav")
    sf.write(full_path, full, model.sampling_rate)
    logging.info("Done. Full narration: %s (%.1fs)", full_path, len(full) / model.sampling_rate)


if __name__ == "__main__":
    main()
