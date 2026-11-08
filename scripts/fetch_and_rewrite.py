"""Pick today's science story from several outlets (the one young kids
would find most exciting, skipping anything covered recently or unsuitable)
and rewrite it as a very easy Korean narration script, plus a short topic
keyword for the KakaoTalk message (scene-per-paragraph, matching
narrate.py's format).

Requires the ANTHROPIC_API_KEY environment variable.
"""

import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kst  # noqa: E402
from news_sources import fetch_all_candidates  # noqa: E402
from topic_history import append_history, read_history  # noqa: E402

MODEL = "claude-haiku-5-5"

PICK_PROMPT = """당신은 초등학생 아이들에게 매일 아침 들려줄 과학 뉴스를 고르는 편집자입니다.
아래 후보 기사 목록에서 오늘 들려줄 기사를 딱 하나 고르세요.

고르는 기준 (위에 있을수록 중요):
1. 빼야 할 것: 재난, 사망, 질병, 의료, 전쟁, 범죄, 마약, 술, 성, 정치, 경제, 정책, 날씨 예보,
   무섭거나 슬픈 내용. 이런 기사는 아무리 흥미로워도 고르지 마세요.
2. 초등학생이 듣자마자 우와 할 주제: 동물, 공룡과 화석, 우주와 행성, 우리 몸의 신기한 점,
   바다, 곤충, 로봇, 기상천외한 발견.
3. 최근 다룬 주제와 다른 분야를 고르세요. 어제 우주였다면 오늘은 동물처럼요.
4. 최근에 쓴 매체와 다른 매체를 우선하세요.
5. 설명이 짧게 끝나는 단순한 발견을 고르세요. 원리가 복잡한 연구는 피하세요.

출력은 JSON 한 줄만: {"index": 후보 번호, "reason": "고른 이유 한 문장"}"""

WRITE_PROMPT = """당신은 7~10살 아이에게 과학 소식을 들려주는 다정한 이야기꾼입니다.
아래 과학 뉴스 한 건을, 초등학교 1~3학년이 한 번 듣고 바로 이해할 수 있는
약 4분 분량(한국어 약 1400~1800자)의 이야기로 들려주세요.

출력 형식 (반드시 지키세요):
- 첫 줄에 "주제: " 뒤에 아이가 바로 알아듣는 쉬운 낱말 하나로 주제를 써주세요
  (예: 주제: 공룡 / 주제: 개미 / 주제: 달).
- 그다음 줄은 비워두세요.
- 그 아래부터 이야기 본문을 쓰세요.

쉽게 쓰는 규칙 (가장 중요해요):
- 한 문장은 짧게, 한 문장에는 한 가지만 말하세요.
- 기사 내용을 다 전하려 하지 마세요. 가장 신기한 사실 한두 개에만 집중하세요.
- 어려운 낱말, 전문 용어, 영어 이름, 연구 기관 이름은 되도록 빼세요.
  꼭 필요한 새 낱말은 이야기 전체에서 한두 개만 쓰고, 아이가 아는 것에 빗대어 바로 풀어주세요
  (예: 망원경은 아주 멀리까지 보는 커다란 눈이에요).
- 큰 숫자, 퍼센트, 단위는 아이가 아는 것으로 바꾸세요
  (예: 축구장 열 개만큼, 우리 반 친구들을 다 합친 것보다 무거워요).
- 원리를 설명할 때는 한 단계만, 집이나 학교에서 본 장면에 빗대어 말하세요.
- 중간중간 아이에게 묻거나 상상하게 해주세요 (예: 여러분이 개미라면 어떨까요?).
- 실제 뉴스 내용을 바꾸거나 부풀리지 마세요.

이야기 흐름:
- 첫 장면: 밝은 아침 인사, 그리고 이 소식을 어디서 가져왔는지 한 번 말하기
  (예: 좋은 아침이에요! 오늘은 {출처}에 실린 신기한 소식을 가져왔어요).
- 마지막 장면: 요약하지 말고, 짧고 따뜻한 작별 인사로 끝내기 (예: 그럼 오늘은 여기까지! 내일 또 만나요).
- 주제 줄을 뺀 본문은 6~9개 장면으로 나누고, 장면 사이는 반드시 빈 줄 하나로 구분하세요.
- 친근하고 신나는 ~해요체, 음성합성으로 자연스럽게 읽히는 완결된 문장만 쓰세요.
- 따옴표, 괄호, 별표, 이모지 같은 특수문자는 쓰지 마세요.
- 주제 줄과 본문만 출력하고, 제목이나 설명은 쓰지 마세요."""


def _claude(system: str, user: str, max_tokens: int) -> dict:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def _text(data: dict) -> str:
    return "".join(b["text"] for b in data["content"] if b.get("type") == "text").strip()


def pick_article(candidates: list[dict], history: list[dict]) -> dict:
    recent = history[-10:]
    recent_lines = "\n".join(
        f"- {h.get('date', '')}: {h.get('topic', '')} ({h.get('source', '사이언스데일리')})" for h in recent
    ) or "- 없음"
    cand_lines = "\n".join(
        f"[{i}] {c['source']} | {c['title']} | {c['description'][:160]}" for i, c in enumerate(candidates)
    )
    user = f"최근 다룬 주제:\n{recent_lines}\n\n후보 기사:\n{cand_lines}"
    try:
        raw = _text(_claude(PICK_PROMPT, user, 300))
        match = re.search(r"\{.*\}", raw, re.S)
        choice = json.loads(match.group(0)) if match else {}
        idx = int(choice.get("index", -1))
        if 0 <= idx < len(candidates):
            print("picked:", candidates[idx]["title"], "|", choice.get("reason", ""))
            return candidates[idx]
        print("picker returned an out-of-range index, falling back:", raw)
    except Exception as exc:  # noqa: BLE001 -- picking must never block the morning run
        print("picker failed, falling back to first candidate:", exc)
    return candidates[0]


def rewrite_for_kids(article: dict) -> tuple[str, str]:
    user = (
        f"오늘 날짜: {kst.today().isoformat()}\n"
        f"출처: {article['source']}\n"
        f"뉴스 제목: {article['title']}\n"
        f"뉴스 요약: {article['description']}\n\n"
        "위 뉴스로 아이들이 들을 아침 과학 이야기를 써주세요. 첫 장면에서 출처를 위 이름 그대로 말해주세요."
    )
    data = _claude(WRITE_PROMPT, user, 8000)
    text = _text(data)

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

    pool = fetch_all_candidates()
    candidates = [c for c in pool if c["link"] not in used_links] or pool
    if not candidates:
        raise RuntimeError("No science news candidates from any feed")

    article = pick_article(candidates, history)
    print(f"source article: [{article['source']}] {article['title']}\n{article['link']}")

    topic, story = rewrite_for_kids(article)
    print("topic:", topic)

    append_history(
        repo_slug,
        github_token,
        {
            "date": kst.today().isoformat(),
            "source": article["source"],
            "title": article["title"],
            "link": article["link"],
            "topic": topic,
        },
    )
    return topic, story


if __name__ == "__main__":
    t, s = build_todays_story(
        repo_slug=os.environ.get("REPO_SLUG", "Zed-leo-23/voice-story-narrator"),
        github_token=os.environ["GITHUB_TOKEN"],
    )
    print("TOPIC:", t)
    print(s)
