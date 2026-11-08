"""Orchestrates the full daily pipeline:

  ScienceDaily RSS -> Claude rewrite -> narrate.py (voice clone) ->
  GitHub Release upload (backup/archive) -> Firebase Hosting (the link
  actually sent, so KakaoTalk shows a *.web.app domain instead of
  github.com) -> KakaoTalk notification.

Designed to be called from a Kaggle kernel (see kaggle_kernel/), but has
no Kaggle-specific code itself so it can be tested anywhere.

Required environment variables: ANTHROPIC_API_KEY, GITHUB_TOKEN,
KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN. KAKAO_CLIENT_SECRET is required
only if the Kakao app has "클라이언트 시크릿" (Client Secret) enabled.
FIREBASE_PROJECT_ID, FIREBASE_SITE_ID, FIREBASE_SERVICE_ACCOUNT_JSON are
optional -- without them the GitHub Release link is sent instead.
"""

import datetime
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kst  # noqa: E402
from fetch_and_rewrite import build_todays_story  # noqa: E402
from firebase_hosting import deploy_narration_page  # noqa: E402
from github_release import upload_release_asset  # noqa: E402
from kakao import send_link_to_me  # noqa: E402


def korean_date_str(d: datetime.date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일"


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

    print("[1/5] fetching + rewriting today's science story ...")
    topic, story_text = build_todays_story(repo_slug=repo_slug, github_token=os.environ["GITHUB_TOKEN"])
    story_path = os.path.join(outdir, "today_story.txt")
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(story_text)
    print(story_text[:200] + "...")

    print("[2/5] generating narration ...")
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
            # Slightly brisker than the 1.0 default -- aimed at a brighter,
            # more awake morning feel. Tell Claude to tune this further if
            # it's still not energetic enough (or overshoots).
            "--speed", "1.05",
        ],
        env=env,
        check=True,
    )

    today = kst.today()
    today_iso = today.isoformat()
    title = f"{korean_date_str(today)}_어린이 과학뉴스 ({topic})"
    wav_path = os.path.join(outdir, "full_story.wav")

    print("[3/5] uploading to GitHub Release (backup/archive) ...")
    backup_link = upload_release_asset(
        repo=repo_slug,
        tag=f"daily-{today_iso}",
        title=title,
        asset_path=wav_path,
        token=os.environ["GITHUB_TOKEN"],
    )
    print("backup link:", backup_link)

    print("[4/5] publishing to Firebase Hosting ...")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID")
    firebase_site_id = os.environ.get("FIREBASE_SITE_ID")
    firebase_sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if firebase_site_id and firebase_sa_json:
        with open(wav_path, "rb") as f:
            audio_bytes = f.read()
        link = deploy_narration_page(
            project_id=firebase_project_id or "",
            site_id=firebase_site_id,
            service_account_json=firebase_sa_json,
            title=title,
            audio_bytes=audio_bytes,
        )
        print("firebase link:", link)
    else:
        print("Firebase not configured (FIREBASE_SITE_ID / FIREBASE_SERVICE_ACCOUNT_JSON missing) -- falling back to the GitHub Release link.")
        link = backup_link

    print("[5/5] sending to KakaoTalk ...")
    send_link_to_me(
        text=f"오늘의 어린이 과학기사({topic})가 도착했어요 ({today_iso})",
        link=link,
        refresh_token=os.environ["KAKAO_REFRESH_TOKEN"],
        rest_api_key=os.environ["KAKAO_REST_API_KEY"],
        client_secret=os.environ.get("KAKAO_CLIENT_SECRET"),
    )
    print("done.")


if __name__ == "__main__":
    main(
        engine_path=os.environ.get("ENGINE_PATH", "/kaggle/working/voicestudio"),
        ref_audio_search_dirs=[os.environ.get("REF_AUDIO_DIR", "/kaggle/input")],
        outdir=os.environ.get("OUTDIR", "/kaggle/working/output"),
    )
