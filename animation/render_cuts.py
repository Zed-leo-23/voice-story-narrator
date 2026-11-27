"""Draw one picture per shot with open-source SDXL (free GPU, e.g. Kaggle).

    python3 animation/render_cuts.py tiger-persimmon                 # every shot
    python3 animation/render_cuts.py tiger-persimmon --shots 1,2     # a quick test
    python3 animation/render_cuts.py tiger-persimmon --dry-run       # print prompts only, no GPU

Writes animation/out/<id>/shot_01.png ... (1920x1080) and contact_sheet.jpg.
Prompts come from animation/stories/<id>.json and style.py, rebuilt for SDXL:
a few style words, the scene, the character looks, a few more style words.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from style import CHARACTERS, DEFAULT_LOOK, LOOKS, LORAS, NEGATIVE, STYLE_TAGS, STYLE_TAGS_END  # noqa: E402

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


def prompt_for(shot: dict, look: str = "base") -> str:
    """Short style words, then the scene and who is in it. The long STYLE text is
    left out: in SDXL it drowned the scene (no snow, no tiger in the 2nd test)."""
    looks = " ".join(f"{c}: {english(CHARACTERS[c])}." for c in shot["characters"] if c in CHARACTERS)
    triggers = ", ".join(LORAS[name][2] for name in LOOKS[look])
    return clean(f"{triggers + ', ' if triggers else ''}{STYLE_TAGS}. {shot['picture']}. {looks} {STYLE_TAGS_END}")


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
    names = sorted({n for look in LOOKS.values() for n in look})
    for name in names:
        repo, weight_file, _ = LORAS[name]
        pipe.load_lora_weights(repo, weight_name=weight_file, adapter_name=name)
    return pipe


def use_look(pipe, look: str) -> None:
    weights = LOOKS[look]
    if not weights:
        pipe.disable_lora()
        return
    pipe.enable_lora()
    pipe.set_adapters(list(weights), adapter_weights=list(weights.values()))


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


def contact_sheet(paths: list[str], out: str, cols: int = 4) -> None:
    from PIL import Image

    w, h = 480, 270
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
    ap.add_argument("--looks", default=os.environ.get("ANIMATION_LOOKS") or DEFAULT_LOOK,
                    help=f"comma list of {', '.join(LOOKS)}; more than one = one picture per look to compare")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.load(open(os.path.join(HERE, "stories", f"{args.story}.json"), encoding="utf-8"))
    wanted = {int(s) for s in args.shots.split(",") if s.strip()}
    shots = [s for s in data["shots"] if not wanted or s["shot"] in wanted]
    out = args.out or os.path.join(HERE, "out", args.story)
    os.makedirs(out, exist_ok=True)
    negative = clean(data.get("negative_prompt") or NEGATIVE)
    looks = [x.strip() for x in args.looks.split(",") if x.strip()]
    unknown = [x for x in looks if x not in LOOKS]
    if unknown:
        raise SystemExit(f"unknown look {unknown}; choose from {list(LOOKS)}")

    if args.dry_run:
        for s in shots:
            for look in looks:
                print(f"--- shot {s['shot']} [{look}] ({s['start']:.1f}-{s['end']:.1f}s)\n{prompt_for(s, look)}")
        print(f"--- negative\n{negative}")
        return

    import torch
    from PIL import Image

    pipe = load_pipe(args.model)
    done = []  # (path, shot, look)
    for look in looks:
        use_look(pipe, look)
        for s in shots:
            name = f"shot_{s['shot']:02d}.png" if len(looks) == 1 else f"shot_{s['shot']:02d}_{look}.png"
            path = os.path.join(out, name)
            print(f"[{look}] shot {s['shot']}/{len(data['shots'])}: {s['picture'][:60]}", flush=True)
            image = pipe(
                **embeddings(pipe, prompt_for(s, look), negative),
                width=WIDTH, height=HEIGHT,
                num_inference_steps=args.steps, guidance_scale=args.guidance,
                generator=torch.Generator("cuda").manual_seed(args.seed + s["shot"]),
            ).images[0]
            image.resize(FINAL, Image.LANCZOS).save(path)
            done.append((path, s, look))
    # Same shot side by side across looks: one row per shot when comparing.
    done.sort(key=lambda d: (d[1]["shot"], looks.index(d[2])))
    contact_sheet([p for p, _, _ in done], os.path.join(out, "contact_sheet.jpg"), cols=len(looks) if len(looks) > 1 else 4)
    json.dump({"story": args.story, "model": args.model, "seed": args.seed, "steps": args.steps, "looks": looks,
               "loras": {n: LORAS[n] for look in looks for n in LOOKS[look]},
               "shots": {os.path.basename(p): prompt_for(s, look) for p, s, look in done}},
              open(os.path.join(out, "prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(done)} pictures in {out}")


if __name__ == "__main__":
    main()
