"""When a run fails on Kaggle, save what went wrong to this repo
(automation_state/run_logs/last_error.txt) so it can be read without anyone
opening Kaggle. Secret values from the environment are blanked out first.
"""

import base64
import os
import re

import requests

API = "https://api.github.com"
PATH = "automation_state/run_logs/last_error.txt"


def _redact(text: str) -> str:
    for key, value in os.environ.items():
        if value and len(value) >= 8 and re.search(r"KEY|TOKEN|SECRET|PAT|PASSWORD|JSON", key, re.I):
            text = text.replace(value, f"<{key}>")
    return text


def tail(path: str, lines: int = 80) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return "(no log file)"


def report_error(repo: str, token: str, title: str, body: str) -> None:
    """Best effort: a failure to report must never hide the original error."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        resp = requests.get(f"{API}/repos/{repo}/contents/{PATH}", headers=headers, timeout=20)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        payload = {
            "message": f"Run error: {title}"[:72],
            "content": base64.b64encode(_redact(f"{title}\n\n{body}").encode("utf-8")).decode("ascii"),
        }
        if sha:
            payload["sha"] = sha
        requests.put(f"{API}/repos/{repo}/contents/{PATH}", headers=headers, json=payload, timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"(could not save the error report: {exc!r})")
