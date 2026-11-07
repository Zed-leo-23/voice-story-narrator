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
import logging
import os

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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--story", required=True, help="Text file; scenes separated by a blank line")
    p.add_argument("--ref_audio", required=True, help="Clean reference recording of your voice (wav)")
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

    if args.ref_text is None:
        # Auto-picking a passage from a reference clip needs a loaded ASR
        # model. The library's own implicit fallback only reuses an ASR
        # snapshot already cached by the desktop app's Model Catalogue and
        # refuses to download one, so load it explicitly here instead.
        logging.info("No --ref_text given; loading ASR for automatic reference transcription ...")
        model.load_asr_model()

    gap = np.zeros(int(args.gap_seconds * model.sampling_rate), dtype=np.float32)
    pieces: list[np.ndarray] = []

    for i, scene in enumerate(scenes, 1):
        logging.info("[%d/%d] generating: %s...", i, len(scenes), scene[:50])
        audios = model.generate(
            text=scene,
            language=args.language,
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
            num_step=args.num_step,
            guidance_scale=args.guidance_scale,
            speed=args.speed,
        )
        wav = audios[0].squeeze().detach().cpu().float().numpy()
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
