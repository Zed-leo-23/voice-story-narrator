"""Send a KakaoTalk "나에게 보내기" (message to me) notification with a link,
using a long-lived refresh token (set up once, see SETUP_AUTOMATION.md).
"""

import json

import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def _refresh_access_token(refresh_token: str, rest_api_key: str) -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": refresh_token,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_link_to_me(text: str, link: str, refresh_token: str, rest_api_key: str) -> None:
    access_token = _refresh_access_token(refresh_token, rest_api_key)
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "나레이션 듣기",
    }
    resp = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template)},
        timeout=20,
    )
    resp.raise_for_status()
