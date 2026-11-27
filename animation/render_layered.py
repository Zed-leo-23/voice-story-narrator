"""Layered cuts: backgrounds and character sprites drawn apart, then put together.

    python3 animation/render_layered.py tiger-persimmon               # every shot
    python3 animation/render_layered.py tiger-persimmon --shots 1,4   # only these shots
    python3 animation/render_layered.py tiger-persimmon --dry-run     # print prompts only

Plan: animation/layers.py. Writes animation/out/<id>/
  layers/bg_<name>.png         background, no characters (1920x1080)
  layers/sprite_<name>.png     one character pose, cut out (transparent PNG)
  shot_01.png ...              sprites placed on backgrounds (1920x1080)
  layout.json                  which layers make each shot and where (for animating later)
  contact_sheet.jpg, prompts.json

Each character's first sprite is its reference picture; every later sprite of
that character gets it through IP-Adapter so the character keeps one look.
"""
import argparse, json, os, re, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from layers import STORIES  # noqa: E402
from render_cuts import FINAL, MODEL, clean, contact_sheet, embeddings, english, load_pipe, use_look  # noqa: E402
from style import (  # noqa: E402
    BUILDINGS, CHARACTERS, DEFAULT_LOOK, KOREAN_PLACE, LOOKS, LORAS, NEGATIVE, SPRITE_TAGS, STYLE_TAGS, TIME_OF_DAY,
)

BG_SIZE = (1344, 768)
SPRITE_SIZE = (1024, 1024)
IP_ADAPTER = ("h94/IP-Adapter", "sdxl_models", "ip-adapter_sdxl.safetensors")
IP_SCALE = 0.55  # how strongly a sprite copies its character's reference picture
NIGHT_TINT = (0.80, 0.84, 1.0)  # sprites drawn in white light, darkened a little for night shots


def seed(name: str) -> int:
    return zlib.crc32(name.encode()) % 1_000_000


def triggers(look: str) -> str:
    return ", ".join(LORAS[n][2] for n in LOOKS[look])


def background_prompt(time: str | None, place: str, look: str) -> tuple[str, str]:
    lead = ", ".join(x for x in (triggers(look), TIME_OF_DAY[time][0] if time else "") if x)
    buildings = BUILDINGS[1] + ". " if re.search(rf"\b({BUILDINGS[0]})\b", place.lower()) else ""
    prompt = clean(f"{lead}, {place}. empty scene, no characters. {STYLE_TAGS}. {buildings}{KOREAN_PLACE}. "
                   f"limited soft color palette, minimal details, wide 16:9 background")
    # Silhouettes on a paper window are part of some backgrounds; otherwise keep everyone out.
    keep_out = "tiger, animal, cow, character" + ("" if re.search(r"silhouette|shadow", place) else
                                                 ", people, person, man, woman, child")
    negative = f"{NEGATIVE}, {keep_out}" + (f", {TIME_OF_DAY[time][1]}" if time else "")
    return prompt, clean(negative)


def sprite_prompt(chars: list[str], pose: str, look: str) -> tuple[str, str]:
    looks = " ".join(f"{c.replace('_', ' ')}: {english(CHARACTERS[c])}." for c in chars)
    count = (f"only one {chars[0].replace('_', ' ')}" if len(chars) == 1
             else "exactly these: " + " and ".join(c.replace("_", " ") for c in chars))
    prompt = clean(f"{triggers(look)}, {count}, {pose}. {looks} {SPRITE_TAGS}. big round heads, small dot eyes, "
                   f"clear funny expressions, clear pose, limited soft color palette, minimal details, for young children")
    negative = clean(f"{NEGATIVE}, background, scenery, landscape, ground, floor, grass, snow, trees, house, "
                     f"room, frame, border, cast shadow, cropped, cut off")
    return prompt, negative


def references(sprites: dict) -> dict:
    """Character -> the sprite that defines its look (its first single-character sprite)."""
    refs = {}
    for name, (chars, _) in sprites.items():
        if len(chars) == 1:
            refs.setdefault(chars[0], name)
    return refs


def cut_out(image, session=None):
    """White background -> transparent. rembg's anime model when it works, else flood fill from the edges."""
    from PIL import ImageDraw

    if session is not None:
        try:
            from rembg import remove

            out = remove(image, session=session)
            if out.getbbox():
                return out.crop(out.getbbox())
        except Exception as e:  # noqa: BLE001
            print(f"note: rembg failed ({e!r}); using flood fill")
    rgb = image.convert("RGB")
    fill = rgb.convert("L").point(lambda v: 255 if v > 232 else 0)  # near-white
    w, h = fill.size
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2)]:
        if fill.getpixel((x, y)) == 255:
            ImageDraw.floodfill(fill, (x, y), 128)  # only white reachable from the edges is background
    out = rgb.convert("RGBA")
    out.putalpha(fill.point(lambda v: 0 if v == 128 else 255))
    return out.crop(out.getbbox() or (0, 0, w, h))


def place(bg, sprite, x: float, bottom: float, height: float, flip: bool, night: bool):
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    W, H = bg.size
    s = ImageOps.mirror(sprite) if flip else sprite
    h = int(H * height)
    w = max(1, int(s.width * h / s.height))
    s = s.resize((w, h), Image.LANCZOS)
    if night:
        r, g, b, a = s.split()
        r, g, b = (ch.point(lambda v, k=k: int(v * k)) for ch, k in zip((r, g, b), NIGHT_TINT))
        s = Image.merge("RGBA", (r, g, b, a))
    left, top = int(x * W - w / 2), int(bottom * H - h)
    if bottom >= 0.85:  # standing on the ground: a soft shadow under the feet
        shadow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(shadow).ellipse([left + w * 0.12, top + h * 0.95, left + w * 0.88, top + h * 1.03], fill=90)
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        bg = Image.composite(Image.new("RGB", (W, H), (20, 20, 35)), bg, shadow)
    bg.paste(s, (left, top), s)
    return bg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--shots", default="", help="e.g. 1,4 (default: all)")
    ap.add_argument("--out", default="")
    ap.add_argument("--model", default=os.environ.get("ANIMATION_MODEL") or MODEL)
    ap.add_argument("--look", default=os.environ.get("ANIMATION_LOOKS") or DEFAULT_LOOK)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    look = args.look.split(",")[0].strip()
    if look not in LOOKS:
        raise SystemExit(f"unknown look {look!r}; choose from {list(LOOKS)}")

    plan = STORIES[args.story]
    story = json.load(open(os.path.join(HERE, "stories", f"{args.story}.json"), encoding="utf-8"))
    times = {s["shot"]: (s["start"], s["end"]) for s in story["shots"]}
    wanted = {int(s) for s in args.shots.split(",") if s.strip()}
    shots = {n: v for n, v in plan["shots"].items() if not wanted or n in wanted}
    bgs = {b for b, _ in shots.values()}
    refs = references(plan["sprites"])
    used = {p[0] for _, ps in shots.values() for p in ps}
    # Every reference a used sprite depends on is drawn too, references first.
    needed = used | {refs[c] for s in used for c in plan["sprites"][s][0] if c in refs}
    order = [s for s in plan["sprites"] if s in needed and s in refs.values()] + \
            [s for s in plan["sprites"] if s in needed and s not in refs.values()]

    prompts = {}
    for b in sorted(bgs):
        prompts[f"bg_{b}"] = background_prompt(*plan["backgrounds"][b], look)
    for s in order:
        prompts[f"sprite_{s}"] = sprite_prompt(*plan["sprites"][s], look)
    if args.dry_run:
        for k, (p, n) in prompts.items():
            print(f"--- {k}\n{p}\n  [negative] {n}")
        print("--- order:", order)
        return

    import torch
    from PIL import Image

    out = args.out or os.path.join(HERE, "out", args.story)
    layer_dir = os.path.join(out, "layers")
    os.makedirs(layer_dir, exist_ok=True)
    pipe = load_pipe(args.model)
    use_look(pipe, look)
    try:
        pipe.load_ip_adapter(IP_ADAPTER[0], subfolder=IP_ADAPTER[1], weight_name=IP_ADAPTER[2])
        has_ip = True
    except Exception as e:  # noqa: BLE001
        print(f"note: IP-Adapter unavailable ({e!r}); characters may vary between sprites")
        has_ip = False
    blank = Image.new("RGB", (224, 224), "white")

    def draw(key: str, size: tuple[int, int], ref=None):
        prompt, negative = prompts[key]
        extra = {}
        if has_ip:
            pipe.set_ip_adapter_scale(IP_SCALE if ref is not None else 0.0)
            extra["ip_adapter_image"] = ref if ref is not None else blank
        print(f"drawing {key}{' (with reference)' if ref is not None else ''}", flush=True)
        return pipe(**embeddings(pipe, prompt, negative), **extra, width=size[0], height=size[1],
                    num_inference_steps=args.steps, guidance_scale=args.guidance,
                    generator=torch.Generator("cuda").manual_seed(seed(key))).images[0]

    for b in sorted(bgs):
        draw(f"bg_{b}", BG_SIZE).resize(FINAL, Image.LANCZOS).save(os.path.join(layer_dir, f"bg_{b}.png"))

    try:
        from rembg import new_session

        session = new_session("isnet-anime")
    except Exception as e:  # noqa: BLE001
        print(f"note: rembg unavailable ({e!r}); using flood fill")
        session = None
    ref_pictures = {}
    for s in order:
        chars = plan["sprites"][s][0]
        ref = next((ref_pictures[c] for c in chars if c in ref_pictures), None)
        raw = draw(f"sprite_{s}", SPRITE_SIZE, ref)
        raw.save(os.path.join(layer_dir, f"raw_{s}.png"))
        if s in refs.values():
            ref_pictures[chars[0]] = raw
        cut_out(raw, session).save(os.path.join(layer_dir, f"sprite_{s}.png"))

    layout, done = {}, []
    for n, (b, placements) in sorted(shots.items()):
        night = plan["backgrounds"][b][0] == "night"
        frame = Image.open(os.path.join(layer_dir, f"bg_{b}.png")).convert("RGB")
        for sprite, x, bottom, height, flip in placements:
            frame = place(frame, Image.open(os.path.join(layer_dir, f"sprite_{sprite}.png")).convert("RGBA"),
                          x, bottom, height, flip, night)
        path = os.path.join(out, f"shot_{n:02d}.png")
        frame.save(path)
        done.append(path)
        layout[n] = {"start": times[n][0], "end": times[n][1], "background": f"layers/bg_{b}.png",
                     "sprites": [{"file": f"layers/sprite_{s}.png", "x": x, "bottom": bottom, "height": h,
                                  "flip": f, "night_tint": night} for s, x, bottom, h, f in placements]}
    contact_sheet(done, os.path.join(out, "contact_sheet.jpg"))
    json.dump(layout, open(os.path.join(out, "layout.json"), "w"), indent=2)
    json.dump({"story": args.story, "look": look, "model": args.model, "ip_adapter": has_ip,
               "prompts": {k: {"prompt": p, "negative": n} for k, (p, n) in prompts.items()}},
              open(os.path.join(out, "prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(done)} pictures in {out}")


if __name__ == "__main__":
    main()
