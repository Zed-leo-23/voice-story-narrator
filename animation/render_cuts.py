"""Draw one picture per shot with open-source SDXL (free GPU, e.g. Kaggle).

    python3 animation/render_cuts.py tiger-persimmon                 # every shot
    python3 animation/render_cuts.py tiger-persimmon --shots 1,2     # a quick test
    python3 animation/render_cuts.py tiger-persimmon --dry-run       # print prompts only, no GPU

Writes animation/out/<id>/shot_01.png ... (1920x1080) and contact_sheet.jpg.
Prompts come from animation/stories/<id>.json and style.py, rebuilt for SDXL:
scene first (so it is never lost), then the character looks, then the art style.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from style import CHARACTERS, NEGATIVE, STYLE  # noqa: E402

MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
# The stock SDXL VAE turns pictures black in fp16; this one is the same VAE fixed for fp16.
VAE = "madebyollin/sdxl-vae-fp16-fix"
WIDTH, HEIGHT = 1344, 768  # SDXL's own 16:9-ish size; upscaled to 1920x1080 after
FINAL = (1920, 1080)


def english(look: str) -> str:
    """'호랑이: big orange tiger ...' -> 'big orange tiger ...' (SDXL can't read Korean)."""
    return re.sub(r"^[^:]*[가-힣][^:]*:\s*", "", look)


def clean(text: str) -> str:
    """Compel reads ( ) + - as weights; keep the words, drop the syntax."""
    text = re.sub(r"\s*\(", ", ", text).replace(")", "").replace("+", " ").replace("_", " ")
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)
    return re.sub(r"\s*,\s*,", ",", re.sub(r"\s+", " ", text)).strip()


def prompt_for(shot: dict) -> str:
    looks = " ".join(f"{c}: {english(CHARACTERS[c])}." for c in shot["characters"] if c in CHARACTERS)
    # "No text, no letters..." makes SDXL think of text; the negative prompt covers it.
    style = re.sub(r"\s*No text[^.]*\.", "", STYLE)
    return clean(f"{shot['picture']}. {looks} {style}")


def load_pipe(model: str):
    import torch
    from diffusers import AutoencoderKL, StableDiffusionXLPipeline

    vae = AutoencoderKL.from_pretrained(VAE, torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        model, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
    ).to("cuda")
    # Newer diffusers moved VAE slicing from the pipeline onto the VAE itself.
    if hasattr(pipe.vae, "enable_slicing"):
        pipe.vae.enable_slicing()
    return pipe


def embeddings(pipe, prompt: str, negative: str):
    """SDXL reads only ~77 tokens per prompt; Compel lets the whole prompt count."""
    try:
        from compel import Compel, ReturnedEmbeddingsType

        compel = Compel(
            tokenizer=[pipe.tokenizer, pipe.tokenizer_2],
            text_encoder=[pipe.text_encoder, pipe.text_encoder_2],
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=[False, True],
            truncate_long_prompts=False,
        )
        cond, pooled = compel([prompt, negative])
        return dict(prompt_embeds=cond[0:1], pooled_prompt_embeds=pooled[0:1],
                    negative_prompt_embeds=cond[1:2], negative_pooled_prompt_embeds=pooled[1:2])
    except Exception as e:  # noqa: BLE001 -- any Compel problem: still draw, just truncated
        print(f"note: Compel unavailable ({e!r}); long prompts are cut at 77 tokens")
        return dict(prompt=prompt, negative_prompt=negative)


def contact_sheet(paths: list[str], out: str) -> None:
    from PIL import Image

    cols, w, h = 4, 480, 270
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "white")
    for i, p in enumerate(paths):
        sheet.paste(Image.open(p).resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out, quality=88)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--shots", default="", help="e.g. 1,2,5 (default: all)")
    ap.add_argument("--out", default="")
    ap.add_argument("--model", default=os.environ.get("ANIMATION_MODEL") or MODEL)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=1234, help="same seed + same prompt = same picture")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.load(open(os.path.join(HERE, "stories", f"{args.story}.json"), encoding="utf-8"))
    wanted = {int(s) for s in args.shots.split(",") if s.strip()}
    shots = [s for s in data["shots"] if not wanted or s["shot"] in wanted]
    out = args.out or os.path.join(HERE, "out", args.story)
    os.makedirs(out, exist_ok=True)
    negative = clean(data.get("negative_prompt") or NEGATIVE)

    if args.dry_run:
        for s in shots:
            print(f"--- shot {s['shot']} ({s['start']:.1f}-{s['end']:.1f}s)\n{prompt_for(s)}")
        print(f"--- negative\n{negative}")
        return

    import torch
    from PIL import Image

    pipe = load_pipe(args.model)
    done = []
    for s in shots:
        path = os.path.join(out, f"shot_{s['shot']:02d}.png")
        print(f"shot {s['shot']}/{len(data['shots'])}: {s['picture'][:70]}", flush=True)
        image = pipe(
            **embeddings(pipe, prompt_for(s), negative),
            width=WIDTH, height=HEIGHT,
            num_inference_steps=args.steps, guidance_scale=args.guidance,
            generator=torch.Generator("cuda").manual_seed(args.seed + s["shot"]),
        ).images[0]
        image.resize(FINAL, Image.LANCZOS).save(path)
        done.append(path)
    contact_sheet(done, os.path.join(out, "contact_sheet.jpg"))
    json.dump({"story": args.story, "model": args.model, "seed": args.seed, "steps": args.steps,
               "shots": {os.path.basename(p): prompt_for(s) for p, s in zip(done, shots)}},
              open(os.path.join(out, "prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(done)} pictures in {out}")


if __name__ == "__main__":
    main()
