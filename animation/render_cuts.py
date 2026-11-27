"""Draw one picture per shot with open-source SDXL (free GPU, e.g. Kaggle).

    python3 animation/render_cuts.py tiger-persimmon                 # every shot
    python3 animation/render_cuts.py tiger-persimmon --shots 1,2     # a quick test
    python3 animation/render_cuts.py tiger-persimmon --dry-run       # print prompts only, no GPU

Writes animation/out/<id>/shot_01.png ... (1920x1080) and contact_sheet.jpg.
Prompts come from animation/stories/<id>.json and style.py, rebuilt for SDXL:
a few style words, the scene, the character looks, then the full art style.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from style import CHARACTERS, NEGATIVE, STYLE, STYLE_TAGS  # noqa: E402

MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
# The stock SDXL VAE turns pictures black in fp16; this one is the same VAE fixed for fp16.
VAE = "madebyollin/sdxl-vae-fp16-fix"
WIDTH, HEIGHT = 1344, 768  # SDXL's own 16:9-ish size; upscaled to 1920x1080 after
FINAL = (1920, 1080)


def english(look: str) -> str:
    """'호랑이: big orange tiger ...' -> 'big orange tiger ...' (SDXL can't read Korean)."""
    return re.sub(r"^[^:]*[가-힣][^:]*:\s*", "", look)


def clean(text: str) -> str:
    """Flatten ( ) + - _ into plain words and commas."""
    text = re.sub(r"\s*\(", ", ", text).replace(")", "").replace("+", " ").replace("_", " ")
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)
    return re.sub(r"\s*,\s*,", ",", re.sub(r"\s+", " ", text)).strip()


def prompt_for(shot: dict) -> str:
    looks = " ".join(f"{c}: {english(CHARACTERS[c])}." for c in shot["characters"] if c in CHARACTERS)
    # "No text, no letters..." makes SDXL think of text; the negative prompt covers it.
    style = re.sub(r"\s*No text[^.]*\.", "", STYLE)
    # The look in a few words first: the start of a prompt weighs most.
    return clean(f"{STYLE_TAGS}. {shot['picture']}. {looks} {style}")


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


def _encode(pipe, text: str, chunks: int | None = None):
    """CLIP reads 77 tokens at a time. Split the prompt into 75-token pieces,
    encode each with both SDXL text encoders and join them, so every word counts."""
    import torch

    parts, pooled = [], None
    for tok, enc in ((pipe.tokenizer, pipe.text_encoder), (pipe.tokenizer_2, pipe.text_encoder_2)):
        ids = tok(text, add_special_tokens=False, truncation=False).input_ids
        n = chunks or max(1, -(-len(ids) // 75))
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        hidden = []
        for i in range(n):
            piece = [tok.bos_token_id, *ids[i * 75:(i + 1) * 75], tok.eos_token_id]
            piece += [pad] * (77 - len(piece))
            out = enc(torch.tensor([piece], device=enc.device), output_hidden_states=True)
            hidden.append(out.hidden_states[-2])
            if enc is pipe.text_encoder_2 and pooled is None:
                pooled = out[0]  # projected text embedding of the first piece
        parts.append(torch.cat(hidden, dim=1))
    return torch.cat(parts, dim=-1), pooled, n


def embeddings(pipe, prompt: str, negative: str):
    import torch

    def pieces(text: str) -> int:
        return max(1, -(-len(pipe.tokenizer(text, add_special_tokens=False).input_ids) // 75))

    n = max(pieces(prompt), pieces(negative))  # both sides need the same length
    with torch.no_grad():
        cond, pooled, _ = _encode(pipe, prompt, n)
        ncond, npooled, _ = _encode(pipe, negative, n)
    return dict(prompt_embeds=cond, pooled_prompt_embeds=pooled,
                negative_prompt_embeds=ncond, negative_pooled_prompt_embeds=npooled)


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
