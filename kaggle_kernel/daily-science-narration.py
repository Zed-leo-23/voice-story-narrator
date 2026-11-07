"""Thin bootstrapper that runs on Kaggle's free GPU. Clones the engine and
this repo fresh each run (so it always uses the latest code on GitHub),
then hands off to scripts/daily_pipeline.py.

All actual secrets (ANTHROPIC_API_KEY, GITHUB_TOKEN, KAKAO_REST_API_KEY,
KAKAO_REFRESH_TOKEN) are provided as Kaggle kernel Secrets (Add-ons >
Secrets in the kernel editor), which Kaggle exposes as environment
variables -- nothing is hardcoded here.

Your reference voice recording must be attached to this kernel as a
private Kaggle Dataset (see SETUP_AUTOMATION.md); it shows up under
/kaggle/input/<dataset-slug>/.
"""

import os
import subprocess
import sys

REPO_URL = "https://github.com/Zed-leo-23/voice-story-narrator"
ENGINE_URL = "https://github.com/debpalash/voicestudio"
REPO_DIR = "/kaggle/working/voice-story-narrator"
ENGINE_DIR = "/kaggle/working/voicestudio"


def sh(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    if not os.path.isdir(REPO_DIR):
        sh(["git", "clone", "--depth", "1", REPO_URL, REPO_DIR])
    if not os.path.isdir(ENGINE_DIR):
        sh(["git", "clone", "--depth", "1", ENGINE_URL, ENGINE_DIR])
    sh(["pip", "install", "-q", "-r", f"{REPO_DIR}/requirements.txt"])

    sys.path.insert(0, f"{REPO_DIR}/scripts")
    sys.path.insert(0, REPO_DIR)
    from daily_pipeline import main as run_pipeline  # noqa: E402

    run_pipeline(
        engine_path=ENGINE_DIR,
        ref_audio_search_dirs=["/kaggle/input"],
        outdir="/kaggle/working/output",
    )


if __name__ == "__main__":
    main()
