"""Run only by the GitHub Actions workflow, right before `kaggle kernels
push`. Reads the automation secrets from this job's environment (mapped
from GitHub Actions repository secrets) and prepends them as plain
`os.environ[...] = ...` lines directly into
kaggle_kernel/daily-science-narration.py, so the Kaggle kernel has them
as real environment variables the moment it starts running.

This exists because Kaggle's own kernel Secrets
(kaggle_secrets.UserSecretsClient) were unreliable for API-pushed
script kernels in testing -- "Connection error trying to communicate
with service" even after attaching the secret in the kernel editor.
GitHub Actions secrets are the single source of truth instead.

This script modifies the kernel file IN PLACE in the Actions runner's
checkout only. That checkout is thrown away after the job, and the
change is never committed back to git, so secrets never land in the
repository.
"""

import os

SECRET_ENV_MAPPING = {
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    # Named RELEASE_PAT on the GitHub Actions side because a repository
    # secret can't be named GITHUB_TOKEN (that name is reserved for the
    # token Actions injects automatically). Inside the Kaggle kernel it's
    # just called GITHUB_TOKEN like the rest of the pipeline expects.
    "GITHUB_TOKEN": os.environ.get("RELEASE_PAT", ""),
    "KAKAO_REST_API_KEY": os.environ.get("KAKAO_REST_API_KEY", ""),
    "KAKAO_REFRESH_TOKEN": os.environ.get("KAKAO_REFRESH_TOKEN", ""),
    # Only needed if the Kakao app has "클라이언트 시크릿" enabled -- Kakao
    # then requires it on every token call, including refresh, not just the
    # initial login. Empty is fine (kakao.py treats it as optional).
    "KAKAO_CLIENT_SECRET": os.environ.get("KAKAO_CLIENT_SECRET", ""),
}

KERNEL_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "kaggle_kernel", "daily-science-narration.py"
)


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit(
            "Refusing to run outside GitHub Actions: this overwrites "
            "kaggle_kernel/daily-science-narration.py in place with secret "
            "values. Running it locally risks accidentally committing them."
        )

    with open(KERNEL_SCRIPT, encoding="utf-8") as f:
        original = f.read()

    missing = [k for k, v in SECRET_ENV_MAPPING.items() if not v]

    header_lines = ["import os", ""]
    for key, value in SECRET_ENV_MAPPING.items():
        header_lines.append(f"os.environ[{key!r}] = {value!r}")
    header = "\n".join(header_lines) + "\n\n"

    with open(KERNEL_SCRIPT, "w", encoding="utf-8") as f:
        f.write(header + original)

    if missing:
        print("warning: these GitHub repo secrets are empty/not set yet:", missing)
    print(f"injected secrets into {KERNEL_SCRIPT} (local checkout only, not committed)")


if __name__ == "__main__":
    main()
