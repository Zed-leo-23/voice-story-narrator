"""Thin bootstrapper that runs on Kaggle's free GPU. Clones the engine and
this repo fresh each run (so it always uses the latest code on GitHub),
then hands off to scripts/daily_pipeline.py.

Secrets (ANTHROPIC_API_KEY, GITHUB_TOKEN, KAKAO_REST_API_KEY,
KAKAO_REFRESH_TOKEN) are NOT read from Kaggle's own kernel Secrets
feature -- in testing, kaggle_secrets.UserSecretsClient couldn't reach
Kaggle's internal secrets service from an API-pushed script kernel
("Connection error trying to communicate with service"). Instead,
scripts/write_kaggle_secrets.py (run by the GitHub Actions workflow,
which holds the real secrets) prepends `os.environ[...] = ...` lines
directly above this docstring before every `kaggle kernels push`, so by
the time main() below runs, the secrets are already plain environment
variables. This file as committed to git has no secrets in it; they
only exist in the ephemeral Actions runner's checkout for the moment of
the push.

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
