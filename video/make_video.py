"""Assemble one story's video from its narration + timeline.json.

    python3 video/make_video.py \
        --audio  video/samani_full_story.wav \
        --timeline video/samani_timeline.json \
        --outdir video/out/samani

Needs a real timeline.json (written by narrate.py since commit dd02896,
uploaded as a release asset alongside full_story.wav -- see docs/youtube-pipeline.md
section 1). Download both with:

    gh release download story-<name> -R Zed-leo-23/voice-story-narrator -D video/

Per scene: one image, a slow Ken Burns zoom, burned-in subtitles from that
scene's lines. Scenes are concatenated and muxed with the narration audio,
then a thumbnail is cut from the first scene's image.

Scene art is only a placeholder here (a flat gradient card with the scene's
line count) -- there is no illustration step yet. Swap scene_card() out, or
feed it real per-scene artwork files, before anything ships to YouTube.
"""

import argparse
import json
import os
import subprocess

WIDTH, HEIGHT = 1920, 1080
FPS = 30
THUMB_SIZE = (1280, 720)

# Homebrew's plain `ffmpeg` formula is built without libass, so it has no
# `subtitles` filter -- use `ffmpeg-full` (brew install ffmpeg-full) if present.
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg" if os.path.exists("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg") else "ffmpeg"

# Placeholder-only: a small fixed palette cycled by scene number so scenes
# are visually distinct without pretending to be real art.
PLACEHOLDER_PALETTE = [
    ((255, 214, 165), (255, 154, 158)),
    ((168, 230, 207), (56, 173, 169)),
    ((255, 241, 181), (255, 183, 94)),
    ((199, 206, 234), (161, 196, 253)),
    ((255, 201, 222), (253, 160, 133)),
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def scene_card(scene_index: int, lines: list[dict], outpath: str) -> None:
    """Placeholder scene art: a gradient card with the scene number and line
    count, so the pipeline can be assembled and timed before real art exists."""
    from PIL import Image, ImageDraw, ImageFont

    top, bottom = PLACEHOLDER_PALETTE[(scene_index - 1) % len(PLACEHOLDER_PALETTE)]
    img = Image.new("RGB", (WIDTH, HEIGHT))
    px = img.load()
    for y in range(HEIGHT):
        t = y / HEIGHT
        row = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        for x in range(0, WIDTH, 4):  # step by 4, fill block: fast enough for a placeholder
            px[x, y] = row
            px[min(x + 1, WIDTH - 1), y] = row
            px[min(x + 2, WIDTH - 1), y] = row
            px[min(x + 3, WIDTH - 1), y] = row
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 140)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
        small = font
    label = f"Scene {scene_index}"
    bbox = draw.textbbox((0, 0), label, font=font)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, (HEIGHT - (bbox[3] - bbox[1])) / 2 - 40),
               label, fill=(40, 30, 30), font=font)
    draw.text((40, HEIGHT - 70), "PLACEHOLDER ART -- not for upload", fill=(40, 30, 30), font=small)
    img.save(outpath)


def srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(timeline: dict, outpath: str) -> None:
    entries = []
    for scene in timeline["scenes"]:
        for line in scene["lines"]:
            entries.append(line)
    entries.sort(key=lambda l: l["start"])
    with open(outpath, "w", encoding="utf-8") as f:
        for i, line in enumerate(entries, 1):
            f.write(f"{i}\n{srt_timestamp(line['start'])} --> {srt_timestamp(line['end'])}\n{line['text']}\n\n")


def ken_burns_clip(image_path: str, duration: float, outpath: str, zoom_from: float = 1.0, zoom_to: float = 1.08) -> None:
    """A slow zoom-in over `duration` seconds, rendered at WIDTHxHEIGHT/FPS."""
    frames = max(1, round(duration * FPS))
    zoom_expr = f"'{zoom_from}+({zoom_to}-{zoom_from})*on/{frames}'"
    run([
        FFMPEG, "-y", "-loop", "1", "-i", image_path,
        "-vf",
        f"scale={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z={zoom_expr}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}",
        "-frames:v", str(frames), "-pix_fmt", "yuv420p", outpath,
    ])


def build(audio_path: str, timeline_path: str, script_text_path: str | None, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    with open(timeline_path, encoding="utf-8") as f:
        timeline = json.load(f)

    srt_path = os.path.join(outdir, "subtitles.srt")
    write_srt(timeline, srt_path)
    print(f"subtitles: {srt_path}")

    scene_clip_paths = []
    for scene in timeline["scenes"]:
        idx = scene["scene"]
        duration = scene["end"] - scene["start"]
        card_path = os.path.join(outdir, f"scene_{idx:02d}.png")
        clip_path = os.path.join(outdir, f"scene_{idx:02d}.mp4")
        scene_card(idx, scene["lines"], card_path)
        ken_burns_clip(card_path, duration, clip_path)
        scene_clip_paths.append(clip_path)

    concat_list = os.path.join(outdir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in scene_clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    silent_path = os.path.join(outdir, "video_silent.mp4")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", silent_path])

    subbed_path = os.path.join(outdir, "video_subtitled.mp4")
    run([
        FFMPEG, "-y", "-i", silent_path,
        "-vf", f"subtitles={srt_path}:force_style=FontName=AppleGothic\\,FontSize=26\\,PrimaryColour=&HFFFFFF&\\,OutlineColour=&H000000&\\,BorderStyle=1\\,Outline=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", subbed_path,
    ])

    final_path = os.path.join(outdir, "final.mp4")
    run([
        FFMPEG, "-y", "-i", subbed_path, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", final_path,
    ])
    print(f"final video: {final_path}")

    thumb_source = os.path.join(outdir, "scene_01.png")
    thumb_path = os.path.join(outdir, "thumbnail.jpg")
    run([FFMPEG, "-y", "-i", thumb_source, "-vf", f"scale={THUMB_SIZE[0]}:{THUMB_SIZE[1]}", "-update", "1", thumb_path])
    print(f"thumbnail: {thumb_path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True, help="full_story.wav")
    p.add_argument("--timeline", required=True, help="timeline.json")
    p.add_argument("--script", default=None, help="original .txt script (unused by the placeholder art; kept for later illustration steps)")
    p.add_argument("--outdir", required=True)
    args = p.parse_args()
    build(args.audio, args.timeline, args.script, args.outdir)


if __name__ == "__main__":
    main()
