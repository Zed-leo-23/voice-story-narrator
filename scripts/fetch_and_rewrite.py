"""Fetch today's science-news item (skipping anything covered recently)
and rewrite it as a kid-friendly Korean narration script, plus a short
topic keyword for the KakaoTalk message (scene-per-paragraph, matching
narrate.py's format).

Requires the ANTHROPIC_API_KEY environment variable.
"""

import datetime
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topic_history import append_history, read_history  # noqa: E402

SCIENCEDAILY_RSS = "https://www.sciencedaily.com/rss/top/science.xml"

SYSTEM_PROMPT = """당신은 초등학생을 위한 과학 이야기 작가입니다.
아래로 주어지는 최신 과학 뉴스 한 건을 소재로, 초등학교 3~6학년이 이해할 수 있는
약 5분 분량(한국어 기준 약 2000~2500자)의 재미있는 과학 이야기를 한국어로 써주세요.

출력 형식 (반드시 지키세요):
- 첫 줄에 "주제: " 뒤에 이 이야기의 핵심 주제를 한두 단어로 써주세요
  (예: 주제: 별자리 / 주제: 공룡 / 주제: 로봇).
- 그다음 줄은 비워두세요.
- 그 아래부터 이야기 본문을 쓰세요.

내용 규칙:
- 전문 용어는 풀어서 쉽게 설명하고, 비유나 예시를 적극 사용하세요.
- 실제 뉴스 내용을 왜곡하지 말고, 핵심 사실은 정확하게 전달하세요.
- 친근하고 신나는 나레이터 말투(~해요체)로 쓰세요.
- 이 이야기는 아침에 듣는 용도입니다. 첫 장면은 밝고 활기찬 아침 인사로 시작하고,
  이 소식이 사이언스데일리라는 해외 과학 뉴스에서 확인된 거라는 걸 자연스럽게
  언급하세요 (예: 오늘은 사이언스데일리에 올라온 소식을 가져왔어요 같은 느낌).
- 마지막 장면은 본문을 요약하지 말고, 자연스럽고 다정한 작별 인사로 끝내세요
  (예: 그럼 오늘 이야기는 여기까지예요, 내일 또 만나요 같은 짧고 따뜻한 인사말 한두 문장).
- 주제 줄과 빈 줄을 제외한 본문은 6~10개의 장면으로 나누고, 장면과 장면 사이는
  반드시 빈 줄 하나로 구분하세요.
- 각 장면은 한국어 음성합성으로 자연스럽게 읽히도록 완결된 문장으로만 쓰세요.
- 따옴표, 괄호, 별표, 이모지 같은 특수문자는 쓰지 마세요.
- 결과물에는 주제 줄과 이야기 본문만 출력하고, 제목이나 설명, 메타 코멘트는 쓰지 마세요.
"""


def fetch_candidate_articles(limit: int = 15) -> list[tuple[str, str, str]]:
    resp = requests.get(SCIENCEDAILY_RSS, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    candidates = []
    for item in root.findall("./channel/item")[:limit]:
        title = (item.findtext("title") or "").strip()
        description = re.sub("<[^<]+?>", "", item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        if link:
            candidates.append((title, description, link))
    return candidates


def pick_unused_article(
    candidates: list[tuple[str, str, str]], used_links: set[str]
) -> tuple[str, str, str]:
    for candidate in candidates:
        if candidate[2] not in used_links:
            return candidate
    # Every recent RSS item was already covered (feed too slow-moving) --
    # fall back to the top story rather than failing the whole run.
    return candidates[0]


def rewrite_for_kids(title: str, description: str, link: str) -> tuple[str, str]:
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
            "max_tokens": 8000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(block["text"] for block in data["content"] if block.get("type") == "text").strip()

    first_line, _, rest = text.partition("\n")
    topic = first_line.split(":", 1)[-1].strip() if ":" in first_line else first_line.strip()
    story = rest.lstrip("\n").strip()

    if data.get("stop_reason") == "max_tokens":
        print("warning: Claude response hit max_tokens -- trimming any incomplete trailing scene")
        story = _drop_incomplete_tail(story)

    return topic, story


_SENTENCE_ENDERS = (".", "!", "?")


def _drop_incomplete_tail(story: str) -> str:
    """If generation was cut off mid-sentence, drop the last (incomplete)
    scene so the narration never ends mid-word instead of just running
    short by one scene."""
    if story.endswith(_SENTENCE_ENDERS):
        return story
    scenes = story.split("\n\n")
    if len(scenes) <= 1:
        return story  # nothing safe to drop; ship it as-is rather than return empty
    return "\n\n".join(scenes[:-1]).strip()


def build_todays_story(repo_slug: str, github_token: str) -> tuple[str, str]:
    """Returns (topic, story_text)."""
    history = read_history(repo_slug, github_token)
    used_links = {h.get("link") for h in history}

    candidates = fetch_candidate_articles()
    title, description, link = pick_unused_article(candidates, used_links)
    print(f"source article: {title}\n{link}")

    topic, story = rewrite_for_kids(title, description, link)
    print("topic:", topic)

    append_history(
        repo_slug,
        github_token,
        {"date": datetime.date.today().isoformat(), "title": title, "link": link, "topic": topic},
    )
    return topic, story


if __name__ == "__main__":
    t, s = build_todays_story(
        repo_slug=os.environ.get("REPO_SLUG", "Zed-leo-23/voice-story-narrator"),
        github_token=os.environ["GITHUB_TOKEN"],
    )
    print("TOPIC:", t)
    print(s)
