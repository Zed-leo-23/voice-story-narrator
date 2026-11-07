"""Deploy a tiny one-page site (narration title + audio player) to Firebase
Hosting via its REST API, so the link sent over KakaoTalk shows a
*.web.app domain instead of github.com.

Uses a service account JSON (Firebase Hosting Admin role) rather than the
firebase-tools Node CLI, so nothing beyond `requests` + `google-auth` is
needed on the Kaggle kernel.
"""

import gzip
import hashlib
import json

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

HOSTING_API = "https://firebasehosting.googleapis.com/v1beta1"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _access_token(service_account_json: str) -> str:
    info = json.loads(service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds.token


def _gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=9)


def render_page(title: str, audio_filename: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
    background: #fafafa;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
    padding: 24px;
    text-align: center;
  }}
  h1 {{ font-size: 1.25rem; line-height: 1.5; max-width: 420px; }}
  audio {{ width: 100%; max-width: 420px; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <audio controls autoplay src="{audio_filename}"></audio>
</body>
</html>"""


def deploy_narration_page(
    project_id: str,
    site_id: str,
    service_account_json: str,
    title: str,
    audio_bytes: bytes,
    audio_filename: str = "narration.wav",
) -> str:
    token = _access_token(service_account_json)
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "/index.html": render_page(title, audio_filename).encode("utf-8"),
        f"/{audio_filename}": audio_bytes,
    }
    gzipped = {path: _gzip_bytes(content) for path, content in files.items()}
    hashes = {path: hashlib.sha256(data).hexdigest() for path, data in gzipped.items()}

    resp = requests.post(
        f"{HOSTING_API}/sites/{site_id}/versions",
        headers=headers,
        params={"project": project_id} if project_id else None,
        json={"config": {}},
        timeout=30,
    )
    resp.raise_for_status()
    version_name = resp.json()["name"]

    resp = requests.post(
        f"{HOSTING_API}/{version_name}:populateFiles",
        headers=headers,
        json={"files": hashes},
        timeout=30,
    )
    resp.raise_for_status()
    population = resp.json()
    upload_url = population["uploadUrl"]
    required = set(population.get("uploadRequiredHashes", list(hashes.values())))

    for path, digest in hashes.items():
        if digest not in required:
            continue
        up = requests.post(
            f"{upload_url}/{digest}",
            headers={**headers, "Content-Type": "application/octet-stream"},
            data=gzipped[path],
            timeout=120,
        )
        up.raise_for_status()

    resp = requests.patch(
        f"{HOSTING_API}/{version_name}",
        headers=headers,
        params={"updateMask": "status"},
        json={"status": "FINALIZED"},
        timeout=30,
    )
    resp.raise_for_status()

    resp = requests.post(
        f"{HOSTING_API}/sites/{site_id}/releases",
        headers=headers,
        params={"versionName": version_name},
        json={},
        timeout=30,
    )
    resp.raise_for_status()

    return f"https://{site_id}.web.app/"
