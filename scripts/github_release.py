"""Upload a generated narration file as a GitHub Release asset and return
its public download link. Used so the daily pipeline has a stable public
URL to send over KakaoTalk, without hosting anything separately.

Requires a token with Contents: Read and write on the target repo.
"""

import mimetypes
import os

import requests

API = "https://api.github.com"


def upload_release_asset(repo: str, tag: str, title: str, asset_path: str, token: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.post(
        f"{API}/repos/{repo}/releases",
        headers=headers,
        json={
            "tag_name": tag,
            "name": title,
            "body": "Automated daily narration.",
            "draft": False,
            "prerelease": False,
        },
        timeout=30,
    )
    if resp.status_code == 422:
        # A release for this tag already exists (e.g. re-run same day) -- reuse it.
        resp = requests.get(f"{API}/repos/{repo}/releases/tags/{tag}", headers=headers, timeout=30)
    resp.raise_for_status()
    release = resp.json()

    upload_url = release["upload_url"].split("{")[0]
    filename = os.path.basename(asset_path)
    content_type, _ = mimetypes.guess_type(filename)
    with open(asset_path, "rb") as f:
        up = requests.post(
            upload_url,
            headers={**headers, "Content-Type": content_type or "application/octet-stream"},
            params={"name": filename},
            data=f,
            timeout=120,
        )
    up.raise_for_status()
    return up.json()["browser_download_url"]
