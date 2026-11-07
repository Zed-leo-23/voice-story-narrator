"""Fetch today's top science-news item and rewrite it as a kid-friendly
Korean narration script (scene-per-paragraph, matching narrate.py's format).

Requires the ANTHROPIC_API_KEY environment variable.
"""

import datetime
import os
import re
import xml.etree.ElementTree as ET

import requests

SCIENCEDAILY_RSS = "https://www.sciencedaily.com/rss/top/science.xml"

SYSTEM_PROMPT = """당신은 초등학생을 위한 과학 이야기 작가입니다.
아래로 주어지는 최신 과학 뉴스 한 건을 소재로, 초등학교 3~6학년이 이해할 수 있는
약 5분 분량(한국어 기준 약 2000~2500자)의 재미있는 과학 이야기를 한국어로 써주세요.

규칙:
- 전문 용어는 풀어서 쉽게 설명하고, 비유나 예시를 적극 사용하세요.
- 실제 뉴스 내용을 왜곡하지 말고, 핵심 사실은 정확하게 전달하세요.
- 친근하고 신나는 나레이터 말투(~해요체)로 쓰세요.
- 전체를 6~10개의 장면으로 나누고, 장면과 장면 사이는 반드시 빈 줄 하나로 구분하세요.
- 각 장면은 한국어 음성합성으로 자연스럽게 읽히도록 완결된 문장으로만 쓰세요.
- 따옴표, 괄호, 별표, 이모지 같은 특수문자는 쓰지 마세요.
- 결과물에는 이야기 본문만 출력하고, 제목이나 설명, 메타 코멘트는 쓰지 마세요.
"""


def fetch_latest_article() -> tuple[str, str, str]:
    resp = requests.get(SCIENCEDAILY_RSS, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    item = root.find("./channel/item")
    if item is None:
        raise RuntimeError("No items found in RSS feed")
    title = (item.findtext("title") or "").strip()
    description = re.sub("<[^<]+?>", "", item.findtext("description") or "").strip()
    link = (item.findtext("link") or "").strip()
    return title, description, link


def rewrite_for_kids(title: str, description: str, link: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    today = datetime.date.today().isoformat()
    user_prompt = (
        f"오늘 날짜: {today}\n"
        f"뉴스 제목: {title}\n"
        f"뉴스 요약: {description}\n"
        f"원문 링크: {link}\n\n"
        "위 뉴스를 소재로 어린이 과학 나레이션 대본을 작성하세요."
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-5-5",
            "max_tokens": 4000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
    return text.strip()


def build_todays_story() -> str:
    title, description, link = fetch_latest_article()
    print(f"source article: {title}\n{link}")
    return rewrite_for_kids(title, description, link)


if __name__ == "__main__":
    print(build_todays_story())
