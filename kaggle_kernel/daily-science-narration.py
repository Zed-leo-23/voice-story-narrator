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
# The engine changes almost daily upstream; a new version on 2026-11-22 refused
# to load the model. Use one tested version, and move this pin on purpose.
ENGINE_COMMIT = "54465ec203e7a7d68894a09d89c1f6002bc70e59"


def sh(cmd: list[str], redact: str | None = None) -> None:
    shown = [c.replace(redact, "***") for c in cmd] if redact else cmd
    print("+", " ".join(shown))
    subprocess.run(cmd, check=True)


def main() -> None:
    # /kaggle/working survives across saved versions of this same kernel, so
    # skipping the clone when REPO_DIR already exists (as this used to do)
    # means every run after the first keeps using whatever commit happened
    # to be checked out that first time -- silently stale, never the
    # "latest code on GitHub" the docstring above promises. Always discard
    # and re-clone so a push to main actually takes effect the next run.
    if os.path.isdir(REPO_DIR):
        sh(["rm", "-rf", REPO_DIR])
    # voice-story-narrator is a private repo -- an unauthenticated clone 404s.
    token = os.environ.get("GITHUB_TOKEN", "")
    repo_url = REPO_URL.replace("https://", f"https://x-access-token:{token}@") if token else REPO_URL
    # Clone the branch the run was started from (main on the daily schedule),
    # so story branches can be recorded without merging into main first.
    branch = os.environ.get("STORY_BRANCH", "").strip()
    sh(["git", "clone", "--depth", "1", *(["--branch", branch] if branch else []), repo_url, REPO_DIR],
       redact=token or None)
    if not os.path.isdir(ENGINE_DIR):
        sh(["git", "init", "-q", ENGINE_DIR])
        sh(["git", "-C", ENGINE_DIR, "fetch", "-q", "--depth", "1", ENGINE_URL, ENGINE_COMMIT])
        sh(["git", "-C", ENGINE_DIR, "checkout", "-q", "FETCH_HEAD"])
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
