"""Side-by-side voice samples: one passage read with several engine settings,
so a parent can pick the setting that sounds most like them by ear.

Run on the GPU box (via daily_pipeline when automation_state/voice_test.json
names today's date). Writes sample_<label>.wav files to --outdir.
"""

import argparse
import json
import logging
import os

import soundfile as sf
import torch

from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.dtype import tts_dtype_name

# label -> engine settings. A mirrors the old defaults as the baseline.
DEFAULT_VARIANTS = {
    "A": {"chunk_seconds": 15.0, "chunk_threshold": 30.0, "guidance_scale": 2.0, "num_step": 32},
    "B": {"chunk_seconds": 6.0, "chunk_threshold": 8.0, "guidance_scale": 2.0, "num_step": 32},
    "C": {"chunk_seconds": 6.0, "chunk_threshold": 8.0, "guidance_scale": 3.0, "num_step": 32},
    "D": {"chunk_seconds": 6.0, "chunk_threshold": 8.0, "guidance_scale": 3.0, "num_step": 64},
}


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text", required=True)
    p.add_argument("--ref_audio", required=True)
    p.add_argument("--ref_text", default=None)
    p.add_argument("--language", default="Korean")
    p.add_argument("--outdir", default="output")
    p.add_argument("--variants", default=None, help="JSON object label -> settings (default: A-D)")
    p.add_argument("--model", default="k2-fsa/OmniVoice")
    args = p.parse_args()

    variants = json.loads(args.variants) if args.variants else DEFAULT_VARIANTS
    os.makedirs(args.outdir, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = OmniVoice.from_pretrained(args.model, device_map=device, dtype=getattr(torch, tts_dtype_name(device)))
    if args.ref_text is None:
        model.load_asr_model()
    prompt = model.create_voice_clone_prompt(ref_audio=args.ref_audio, ref_text=args.ref_text)
    logging.info("voice sample: %s | transcript: %s", args.ref_audio, prompt.ref_text)

    for label, cfg in variants.items():
        logging.info("sample %s: %s", label, cfg)
        audios = model.generate(
            text=args.text,
            language=args.language,
            voice_clone_prompt=prompt,
            speed=1.0,
            num_step=int(cfg["num_step"]),
            guidance_scale=float(cfg["guidance_scale"]),
            audio_chunk_duration=float(cfg["chunk_seconds"]),
            audio_chunk_threshold=float(cfg["chunk_threshold"]),
        )
        wav = audios[0].squeeze().detach().cpu().float().numpy()
        path = os.path.join(args.outdir, f"sample_{label}.wav")
        sf.write(path, wav, model.sampling_rate)
        logging.info("  saved %s (%.1fs)", path, len(wav) / model.sampling_rate)


if __name__ == "__main__":
    main()
