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
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kst  # noqa: E402
from fetch_and_rewrite import build_todays_story, todays_custom_script  # noqa: E402
from firebase_hosting import deploy_narration_page  # noqa: E402
from github_release import upload_release_asset  # noqa: E402
from kakao import send_link_to_me  # noqa: E402


def korean_date_str(d: datetime.date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일"


AUDIO_EXTENSIONS = {"wav", "m4a", "mp3", "flac", "ogg", "aac"}


VOICES_PATH = os.path.join(REPO_ROOT, "automation_state", "voices.json")
VOICE_TEST_PATH = os.path.join(REPO_ROOT, "automation_state", "voice_test.json")

# Engine settings a voice can override in voices.json ("settings").
DEFAULT_SETTINGS = {"chunk_seconds": 15.0, "chunk_threshold": 30.0, "guidance_scale": 2.0, "num_step": 32}


def list_reference_audio(search_dirs: list[str]) -> list[str]:
    audio = []
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
        audio += [f for f in sorted(all_files) if os.path.splitext(f)[1].lstrip(".").lower() in AUDIO_EXTENSIONS]
    if not audio:
        raise SystemExit(f"No reference audio found under {search_dirs}")
    return audio


def _squash(s: str) -> str:
    # "Yk voice.m4a", "yk_voice", "YK-Voice" all compare equal
    return re.sub(r"[\s_\-]+", "", s).lower()


def load_voices(path: str = VOICES_PATH) -> dict:
    if not os.path.exists(path):
        return {"active": "아빠", "voices": {"아빠": {"file": None, "ref_text": None}}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def voice_settings(cfg: dict, name: str) -> dict:
    return {**DEFAULT_SETTINGS, **(cfg.get("voices", {}).get(name, {}).get("settings") or {})}


def todays_voice_test() -> dict | None:
    """automation_state/voice_test.json with today's KST date -> make comparison
    samples instead of the story. Any other date is ignored, so a leftover
    file can't hijack a later morning."""
    if not os.path.exists(VOICE_TEST_PATH):
        return None
    with open(VOICE_TEST_PATH, encoding="utf-8") as f:
        test = json.load(f)
    dates = test.get("dates") or [test.get("date")]
    return test if kst.today().isoformat() in dates else None


# Comparison samples for a two-paragraph recording: which piece, which settings.
_SHORT_STRONG = {"chunk_seconds": 6.0, "chunk_threshold": 8.0, "guidance_scale": 3.0, "num_step": 32}
PART_VARIANTS = {
    "1": {**DEFAULT_SETTINGS, "ref": "part1"},
    "2": {**_SHORT_STRONG, "ref": "part1"},
    "3": {**_SHORT_STRONG, "ref": "part2"},
    "4": {**_SHORT_STRONG, "ref": "full"},
}


def prepare_refs(engine_path: str, ref_audio: str, ref_text, outdir: str) -> dict:
    """name -> (audio path, transcript or None). A transcript given as two
    paragraphs means the recording is cut at the pause between them, since
    the engine takes at most 20s of audio with a transcript."""
    if isinstance(ref_text, list) and len(ref_text) == 2:
        env = os.environ.copy()
        env["PYTHONPATH"] = engine_path
        out = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "scripts", "cut_reference.py"),
             "--audio", ref_audio, "--outdir", os.path.join(outdir, "ref")],
            env=env, check=True, capture_output=True, text=True,
        ).stdout
        print(out.strip())
        parts = json.loads(out.strip().splitlines()[-1])
        return {
            "part1": (parts["part1"], ref_text[0]),
            "part2": (parts["part2"], ref_text[1]),
            "full": (ref_audio, None),
        }
    if isinstance(ref_text, list):
        ref_text = " ".join(ref_text)
    return {"main": (ref_audio, ref_text)}


def run_voice_test(test: dict, engine_path: str, voice: str, refs: dict, repo_slug: str, outdir: str) -> None:
    variants = test.get("variants") or (PART_VARIANTS if "part1" in refs else None)
    print(f"[voice test] {voice} samples: {variants or 'A-D defaults'}")
    env = os.environ.copy()
    env["PYTHONPATH"] = engine_path
    cmd = [
        sys.executable, os.path.join(REPO_ROOT, "scripts", "voice_test.py"),
        "--text", test["text"],
        "--refs", json.dumps({k: list(v) for k, v in refs.items()}, ensure_ascii=False),
        "--outdir", outdir,
    ]
    if variants:
        cmd += ["--variants", json.dumps(variants)]
    subprocess.run(cmd, env=env, check=True)

    today_iso = kst.today().isoformat()
    for name in sorted(os.listdir(outdir)):
        if name.startswith("sample_") and name.endswith(".wav"):
            link = upload_release_asset(
                repo=repo_slug,
                tag=f"voice-test-{today_iso}",
                title=f"{korean_date_str(kst.today())}_{voice} 목소리 비교 샘플",
                asset_path=os.path.join(outdir, name),
                token=os.environ["GITHUB_TOKEN"],
            )
            print("uploaded:", link)
    print("voice test done (no KakaoTalk message).")


def resolve_voice(search_dirs: list[str], cfg: dict, wanted: str | None) -> tuple[str, str, str | None]:
    """Pick the recording for the wanted voice (엄마/아빠).

    A voice's "file" is a piece of the dataset file name (case, spaces, _ and -
    ignored). A voice with file null takes any recording not claimed by another
    voice -- so a parent can re-upload under any file name. If the wanted
    voice's recording is missing, fall back to whatever voice is there.
    Returns (voice name, audio path, exact transcript or None).
    """
    voices = cfg.get("voices", {})
    wanted = wanted or cfg.get("active") or next(iter(voices), "아빠")
    audio = list_reference_audio(search_dirs)

    def owner(path: str) -> str | None:
        stem = _squash(os.path.basename(path))
        for name, v in voices.items():
            if v.get("file") and _squash(v["file"]) in stem:
                return name
        return None

    def files_for(name: str) -> list[str]:
        v = voices.get(name, {})
        if v.get("file"):
            return [a for a in audio if owner(a) == name]
        return [a for a in audio if owner(a) is None]

    if not files_for(wanted) and len(audio) == 1:
        # Only one recording uploaded (maybe under a new file name): it's the voice asked for.
        print(f"WARNING: '{audio[0]}' doesn't match voice '{wanted}' by name, but it's the only recording -- using it")
        return wanted, audio[0], voices.get(wanted, {}).get("ref_text")

    order = [wanted] + [n for n in voices if n != wanted]
    for name in order:
        found = files_for(name)
        if found:
            if name != wanted:
                print(f"WARNING: no recording for voice '{wanted}' -- using '{name}' instead")
            if len(found) > 1:
                print(f"WARNING: {len(found)} recordings match voice '{name}', using the first: {found}")
            return name, found[0], voices.get(name, {}).get("ref_text")
    # Recordings exist but every one belongs to a voice not in the config.
    print(f"WARNING: could not match any recording to a voice; using {audio[0]} as '{wanted}'")
    return wanted, audio[0], None


def main(
    engine_path: str,
    ref_audio_search_dirs: list[str],
    repo_slug: str = "Zed-leo-23/voice-story-narrator",
    outdir: str = "output",
) -> None:
    os.makedirs(outdir, exist_ok=True)

    print("[0/5] choosing today's voice ...")
    custom = todays_custom_script()
    voices_cfg = load_voices()
    voice, ref_audio, ref_text = resolve_voice(ref_audio_search_dirs, voices_cfg, custom[2] if custom else None)
    settings = voice_settings(voices_cfg, voice)
    refs = prepare_refs(engine_path, ref_audio, ref_text, outdir)

    test = todays_voice_test()
    if test:
        run_voice_test(test, engine_path, voice, refs, repo_slug, outdir)
        return

    use = voices_cfg.get("voices", {}).get(voice, {}).get("use") or next(iter(refs))
    ref_audio, ref_text = refs.get(use) or next(iter(refs.values()))
    print(f"voice: {voice} | piece: {use} | file: {ref_audio} | ref_text: {ref_text or '(auto transcribe)'} | settings: {settings}")

    print("[1/5] fetching + rewriting today's science story ...")
    topic, story_text, kind = build_todays_story(
        repo_slug=repo_slug, github_token=os.environ["GITHUB_TOKEN"], narrator=voice
    )
    story_path = os.path.join(outdir, "today_story.txt")
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(story_text)
    print(story_text[:200] + "...")

    print("[2/5] generating narration ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = engine_path
    cmd = [
        sys.executable, os.path.join(REPO_ROOT, "narrate.py"),
        "--story", story_path,
        "--ref_audio", ref_audio,
        "--language", "Korean",
        "--outdir", outdir,
        # Keep the recording's own pace: changing it made the clone sound
        # less like the real person.
        "--speed", "1.0",
        "--chunk_seconds", str(settings["chunk_seconds"]),
        "--chunk_threshold", str(settings["chunk_threshold"]),
        "--guidance_scale", str(settings["guidance_scale"]),
        "--num_step", str(int(settings["num_step"])),
    ]
    if ref_text:
        # The exact words of the recording -- far better cloning than letting
        # speech recognition guess them.
        cmd += ["--ref_text", ref_text]
    subprocess.run(
        cmd,
        env=env,
        check=True,
    )

    today = kst.today()
    today_iso = today.isoformat()
    label = "오늘의 이야기" if kind == "script" else "어린이 과학뉴스"
    title = f"{korean_date_str(today)}_{label} ({topic})"
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
        text=(
            f"오늘의 이야기({topic})가 도착했어요 ({today_iso})"
            if kind == "script"
            else f"오늘의 어린이 과학기사({topic})가 도착했어요 ({today_iso})"
        ),
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
