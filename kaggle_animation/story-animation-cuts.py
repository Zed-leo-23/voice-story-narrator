"""Runs on Kaggle's free GPU: draws one picture per shot of a story with SDXL,
then uploads them to the GitHub Release `cuts-<story id>`.

Started by .github/workflows/animation-kaggle.yml. Like the daily narration
kernel, the values below (GITHUB_TOKEN, STORY_BRANCH, ANIMATION_STORY,
ANIMATION_SHOTS, ANIMATION_LOOKS, ANIMATION_MODE) are prepended as `os.environ[...] = ...` lines by
scripts/write_kaggle_secrets.py in the Actions runner's throwaway checkout
right before `kaggle kernels push`. This file as committed has no secrets.
"""

import glob
import os
import shutil
import subprocess
import sys

REPO = "Zed-leo-23/voice-story-narrator"
# Not under /kaggle/working: everything there is saved as the kernel's Output,
# and the clone's .git/config holds the GitHub token.
REPO_DIR = "/tmp/voice-story-narrator"


def sh(cmd: list[str], redact: str | None = None) -> None:
    print("+", " ".join(c.replace(redact, "***") for c in cmd) if redact else " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    story = os.environ.get("ANIMATION_STORY", "").strip() or "tiger-persimmon"
    shots = os.environ.get("ANIMATION_SHOTS", "").strip()
    branch = os.environ.get("STORY_BRANCH", "").strip()
    looks = os.environ.get("ANIMATION_LOOKS", "").strip()
    # layered: backgrounds and characters drawn apart, then put together (default).
    # sheets: character sheet candidates only, to choose each character's look.
    # single: one SDXL picture per shot (render_cuts.py).
    mode = os.environ.get("ANIMATION_MODE", "").strip() or "layered"

    if os.path.isdir(REPO_DIR):
        shutil.rmtree(REPO_DIR)
    url = f"https://x-access-token:{token}@github.com/{REPO}" if token else f"https://github.com/{REPO}"
    sh(["git", "clone", "--depth", "1", *(["--branch", branch] if branch else []), url, REPO_DIR],
       redact=token or None)

    subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"])
    # Kaggle already has torch; add the picture libraries only. Kaggle's old torchao
    # makes peft refuse to load LoRAs, and nothing here uses it, so remove it.
    subprocess.run(["pip", "uninstall", "-y", "-q", "torchao"])
    sh(["pip", "install", "-q", "diffusers>=0.30", "transformers", "accelerate", "safetensors", "peft", "requests", "rembg[cpu]"])

    out = f"/kaggle/working/out/{story}"
    if mode in ("layered", "sheets"):
        sh([sys.executable, f"{REPO_DIR}/animation/render_layered.py", story, "--out", out,
            *(["--sheets"] if mode == "sheets" else []),
            *(["--shots", shots] if shots else []), *(["--look", looks] if looks else [])])
    else:
        sh([sys.executable, f"{REPO_DIR}/animation/render_cuts.py", story, "--out", out,
            *(["--shots", shots] if shots else []), *(["--looks", looks] if looks else [])])

    archive = shutil.make_archive(f"/kaggle/working/{story}-cuts", "zip", out)
    if not token:
        print("no GITHUB_TOKEN: pictures stay in this kernel's Output tab only")
        return
    sys.path.insert(0, f"{REPO_DIR}/scripts")
    from github_release import upload_release_asset  # noqa: E402

    files = [archive, f"{out}/contact_sheet.jpg", f"{out}/prompts.json",
             *glob.glob(f"{out}/layout.json"), *sorted(glob.glob(f"{out}/shot_*.png")),
             *sorted(glob.glob(f"{out}/layers/sprite_*.png")), *sorted(glob.glob(f"{out}/sheets/*.png"))]
    for path in files:
        link = upload_release_asset(REPO, f"cuts-{story}", f"Animation cuts: {story}", path, token,
                                    body=f"SDXL shot pictures for {story} (branch {branch or 'default'}).")
        print("uploaded", link, flush=True)


if __name__ == "__main__":
    main()
