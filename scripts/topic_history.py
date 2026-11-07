"""Tracks recently-used ScienceDaily articles in a small JSON file
committed to this repo (automation_state/topic_history.json), via the
GitHub Contents API. Lets the daily pipeline skip articles it already
covered recently, so the topic actually changes day to day.
"""

import base64
import json

import requests

API = "https://api.github.com"
HISTORY_PATH = "automation_state/topic_history.json"
KEEP_LAST = 30


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def read_history(repo: str, token: str) -> list[dict]:
    resp = requests.get(
        f"{API}/repos/{repo}/contents/{HISTORY_PATH}", headers=_headers(token), timeout=20
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content)


def append_history(repo: str, token: str, entry: dict) -> None:
    headers = _headers(token)
    resp = requests.get(f"{API}/repos/{repo}/contents/{HISTORY_PATH}", headers=headers, timeout=20)

    sha = None
    history: list[dict] = []
    if resp.status_code == 200:
        data = resp.json()
        sha = data["sha"]
        history = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    elif resp.status_code != 404:
        resp.raise_for_status()

    history.append(entry)
    history = history[-KEEP_LAST:]

    payload = {
        "message": f"Update topic history ({entry.get('date', '')})",
        "content": base64.b64encode(
            json.dumps(history, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    put = requests.put(
        f"{API}/repos/{repo}/contents/{HISTORY_PATH}", headers=headers, json=payload, timeout=30
    )
    put.raise_for_status()
