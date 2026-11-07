"""Orchestrates the full daily pipeline:

  ScienceDaily RSS -> Claude rewrite -> narrate.py (voice clone) ->
  GitHub Release upload -> KakaoTalk notification.

Designed to be called from a Kaggle kernel (see kaggle_kernel/), but has
no Kaggle-specific code itself so it can be tested anywhere.

Required environment variables: ANTHROPIC_API_KEY, GITHUB_TOKEN,
KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN.
"""

import datetime
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_and_rewrite import build_todays_story  # noqa: E402
from github_release import upload_release_asset  # noqa: E402
from kakao import send_link_to_me  # noqa: E402


AUDIO_EXTENSIONS = {"wav", "m4a", "mp3", "flac", "ogg", "aac"}


def find_reference_audio(search_dirs: list[str]) -> str:
    for d in search_dirs:
        if not os.path.isdir(d):
            print(f"(search dir does not exist: {d})")
            continue
        all_files = []
        for root, _dirs, files in os.walk(d):
            for name in files:
                all_files.append(os.path.join(root, name))
        print(f"found {len(all_files)} file(s) under {d}:")
        for f in all_files:
            print(" ", f)
        for f in sorted(all_files):
            ext = os.path.splitext(f)[1].lstrip(".").lower()
            if ext in AUDIO_EXTENSIONS:
                return f
    raise SystemExit(f"No reference audio found under {search_dirs}")


def main(
    engine_path: str,
    ref_audio_search_dirs: list[str],
    repo_slug: str = "Zed-leo-23/voice-story-narrator",
    outdir: str = "output",
) -> None:
    os.makedirs(outdir, exist_ok=True)

    print("[1/4] fetching + rewriting today's science story ...")
    story_text = build_todays_story()
    story_path = os.path.join(outdir, "today_story.txt")
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(story_text)
    print(story_text[:200] + "...")

    print("[2/4] generating narration ...")
    ref_audio = find_reference_audio(ref_audio_search_dirs)
    print("reference audio:", ref_audio)
    env = os.environ.copy()
    env["PYTHONPATH"] = engine_path
    subprocess.run(
        [
            sys.executable, os.path.join(REPO_ROOT, "narrate.py"),
            "--story", story_path,
            "--ref_audio", ref_audio,
            "--language", "Korean",
            "--outdir", outdir,
        ],
        env=env,
        check=True,
    )

    print("[3/4] uploading to GitHub Release ...")
    today = datetime.date.today().isoformat()
    link = upload_release_asset(
        repo=repo_slug,
        tag=f"daily-{today}",
        title=f"어린이 과학 나레이션 {today}",
        asset_path=os.path.join(outdir, "full_story.wav"),
        token=os.environ["GITHUB_TOKEN"],
    )
    print("link:", link)

    print("[4/4] sending to KakaoTalk ...")
    send_link_to_me(
        text=f"오늘의 어린이 과학기사 나레이션이 도착했어요 ({today})",
        link=link,
        refresh_token=os.environ["KAKAO_REFRESH_TOKEN"],
        rest_api_key=os.environ["KAKAO_REST_API_KEY"],
    )
    print("done.")


if __name__ == "__main__":
    main(
        engine_path=os.environ.get("ENGINE_PATH", "/kaggle/working/voicestudio"),
        ref_audio_search_dirs=[os.environ.get("REF_AUDIO_DIR", "/kaggle/input")],
        outdir=os.environ.get("OUTDIR", "/kaggle/working/output"),
    )
