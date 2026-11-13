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
2. 오늘의 요청 분야가 주어지면, 그 분야에 맞는 기사만 고르세요. 맞는 기사가 하나도 없으면
   억지로 고르지 말고 index를 -1로 하세요.
3. 초등학생이 듣자마자 우와 할 주제: 동물, 공룡과 화석, 우주와 행성, 우리 몸의 신기한 점,
   바다, 곤충, 로봇, 장난감과 발명, 기상천외한 발견.
4. 최근 다룬 주제와 다른 분야를 고르세요. 어제 우주였다면 오늘은 동물처럼요.
5. 최근에 쓴 매체와 다른 매체를 우선하세요.
6. 설명이 짧게 끝나는 단순한 발견을 고르세요. 원리가 복잡한 연구는 피하세요.

출력은 JSON 한 줄만: {"index": 후보 번호 또는 -1, "reason": "고른 이유 한 문장"}"""

REQUESTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "automation_state", "requests.json"
)


def todays_requested_category() -> str | None:
    """automation_state/requests.json maps a KST date ("2026-11-12") to a
    category the family asked for that morning. Edit it on GitHub to
    request a topic for a given day."""
    try:
        with open(REQUESTS_PATH, encoding="utf-8") as f:
            requests_by_date = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return requests_by_date.get(kst.today().isoformat())

CHILD_NAME = os.environ.get("CHILD_NAME", "라온")
NARRATOR = os.environ.get("NARRATOR", "아빠")


def _has_final_consonant(word: str) -> bool:
    last = word[-1]
    return "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0


# 라온 -> 라온아 (calling) / 라온이 (before 가, 의, 에게); 지우 -> 지우야 / 지우
CHILD_CALL = CHILD_NAME + ("아" if _has_final_consonant(CHILD_NAME) else "야")
CHILD_BASE = CHILD_NAME + ("이" if _has_final_consonant(CHILD_NAME) else "")

WRITE_PROMPT = """당신은 __PARENT__입니다. 7~10살 아이 __CHILD__에게 아침마다 과학 소식을 들려줘요.
아래 과학 뉴스 한 건을, 초등학교 1~3학년이 한 번 듣고 바로 이해할 수 있는
약 4분 분량(한국어 약 1400~1800자)의 이야기로 들려주세요.
__PARENT__가 __CHILD__에게 직접 말하듯, 다정하고 신나는 반말로 쓰세요.

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
- 중간중간 __CHILD__에게 묻거나 상상하게 해주세요 (예: __CHILD__가 개미라면 어떨 것 같아?).
- 실제 뉴스 내용을 바꾸거나 부풀리지 마세요.

이야기 흐름:
- 첫 장면은 아래 세 가지를 이 순서로, 자연스럽게 이어서 말하세요. 문장은 그대로 베끼지 말고 조금씩 바꿔도 돼요.
  1) 인사: 안녕! __CALL__? 즐거운 아침이야!
  2) 오늘의 주제: 오늘의 과학 뉴스는 주제 줄에 쓴 바로 그 낱말이야.
  3) 질문 안내: 듣다가 궁금한 게 생기면 __PARENT__한테 말해줘. 적어 뒀다가 __PARENT__가 꼭 대답해 줄게.
- 둘째 장면에서 이 소식을 어디서 가져왔는지 한 번 말하세요 (예: 이건 출처에 실린 소식이야).
- 끝에서 둘째 장면: 갑자기 끝내지 말고 천천히 정리하세요. 오늘 가장 신기했던 사실을 한 문장으로 다시 짚고,
  __CHILD__의 하루와 이어주세요 (예: 오늘 밤 창밖으로 달을 한번 찾아볼까?).
- 마지막 장면: 자, 오늘 이야기는 여기까지야 같은 마무리 신호를 먼저 말하고, 궁금한 게 생각나면
  __PARENT__한테 말해 달라고 한 번 더 부탁한 뒤, 따뜻한 작별 인사로 끝내세요. 두세 문장으로 여유 있게.
- 주제 줄을 뺀 본문은 7~9개 장면으로 나누고, 장면 사이는 반드시 빈 줄 하나로 구분하세요.
- 음성합성으로 자연스럽게 읽히는 완결된 문장만 쓰세요.
- 따옴표, 괄호, 별표, 이모지, 물결표 같은 특수문자는 쓰지 마세요. 물음표와 느낌표는 써도 돼요.
- 주제 줄과 본문만 출력하고, 제목이나 설명은 쓰지 마세요.""".replace("__CALL__", CHILD_CALL).replace("__CHILD__", CHILD_BASE).replace(
    "__PARENT__", NARRATOR
)


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


def _recent_lines(history: list[dict]) -> str:
    return "\n".join(
        f"- {h.get('date', '')}: {h.get('topic', '')} ({h.get('source', '사이언스데일리')})" for h in history[-10:]
    ) or "- 없음"


def pick_article(candidates: list[dict], history: list[dict], category: str | None) -> dict | None:
    """Returns the chosen article, or None when a category was requested
    and no candidate fits it (the caller then tells a story instead)."""
    cand_lines = "\n".join(
        f"[{i}] {c['source']} | {c['title']} | {c['description'][:160]}" for i, c in enumerate(candidates)
    )
    user = f"최근 다룬 주제:\n{_recent_lines(history)}\n\n"
    if category:
        user += f"오늘의 요청 분야: {category}\n\n"
    user += f"후보 기사:\n{cand_lines}"
    try:
        raw = _text(_claude(PICK_PROMPT, user, 300))
        match = re.search(r"\{.*\}", raw, re.S)
        choice = json.loads(match.group(0)) if match else {}
        idx = int(choice.get("index", -1))
        if 0 <= idx < len(candidates):
            print("picked:", candidates[idx]["title"], "|", choice.get("reason", ""))
            return candidates[idx]
        if category and idx == -1:
            print("no news fits the requested category:", choice.get("reason", ""))
            return None
        print("picker returned an out-of-range index, falling back:", raw)
    except Exception as exc:  # noqa: BLE001 -- picking must never block the morning run
        print("picker failed, falling back:", exc)
    return None if category else candidates[0]


def rewrite_for_kids(article: dict | None, category: str | None = None, history: list[dict] | None = None) -> tuple[str, str]:
    if article:
        user = (
            f"오늘 날짜: {kst.today().isoformat()}\n"
            f"출처: {article['source']}\n"
            f"뉴스 제목: {article['title']}\n"
            f"뉴스 요약: {article['description']}\n\n"
            "위 뉴스로 아침 과학 이야기를 써주세요. 둘째 장면에서 출처를 위 이름 그대로 말해주세요."
        )
    else:
        user = (
            f"오늘 날짜: {kst.today().isoformat()}\n"
            f"오늘의 요청 분야: {category}\n"
            f"최근 다룬 주제 (겹치지 않게):\n{_recent_lines(history or [])}\n\n"
            "오늘은 뉴스 대신, 위 분야에 맞는 이야기를 하나 들려주세요. 아이가 알 만한 장난감이나 물건,"
            " 기술 하나를 골라 그것이 처음 어떻게 만들어졌는지 들려주세요. 널리 알려진 확실한 사실만 쓰고,"
            " 확실하지 않은 숫자, 날짜, 이름은 빼세요. 둘째 장면에서 오늘은 뉴스 대신 신기한 탄생 이야기를"
            " 들려준다고 말해주세요."
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


SCRIPTS_DIR = os.path.join(os.path.dirname(REQUESTS_PATH), "scripts")
_UNSPEAKABLE = re.compile(r"[*#_~`>\[\]|]|[\U0001F000-\U0001FFFF☀-➿️]")


def todays_custom_script() -> tuple[str, str] | None:
    """automation_state/scripts/<KST date>.txt, if present, is read aloud as
    written instead of the day's news. Optional first line "주제: 낱말"
    becomes the topic; scenes are separated by blank lines."""
    path = os.path.join(SCRIPTS_DIR, f"{kst.today().isoformat()}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    topic = "이야기"
    first_line, _, rest = text.partition("\n")
    if first_line.strip().startswith("주제") and ":" in first_line:
        topic = first_line.split(":", 1)[1].strip() or topic
        text = rest.strip()
    # Markdown marks and emoji get read out or mangled by TTS; keep words and punctuation.
    text = _UNSPEAKABLE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return topic, text


def build_todays_story(repo_slug: str, github_token: str) -> tuple[str, str, str]:
    """Returns (topic, story_text, kind) where kind is "news" or "script"."""
    custom = todays_custom_script()
    if custom:
        topic, story = custom
        print(f"reading today's custom script (topic: {topic}, {len(story)} chars)")
        append_history(
            repo_slug,
            github_token,
            {
                "date": kst.today().isoformat(),
                "source": "보내준 스크립트",
                "title": f"{topic} 이야기",
                "link": f"script:{kst.today().isoformat()}",
                "topic": topic,
            },
        )
        return topic, story, "script"

    history = read_history(repo_slug, github_token)
    used_links = {h.get("link") for h in history}

    pool = fetch_all_candidates()
    candidates = [c for c in pool if c["link"] not in used_links] or pool
    if not candidates:
        raise RuntimeError("No science news candidates from any feed")

    category = todays_requested_category()
    if category:
        print("requested category for today:", category)

    article = pick_article(candidates, history, category)
    if article:
        print(f"source article: [{article['source']}] {article['title']}\n{article['link']}")
    else:
        print("telling a category story instead of a news article")

    topic, story = rewrite_for_kids(article, category, history)
    print("topic:", topic)

    append_history(
        repo_slug,
        github_token,
        {
            "date": kst.today().isoformat(),
            "source": article["source"] if article else "탄생 이야기",
            "title": article["title"] if article else f"{category} 이야기",
            "link": article["link"] if article else f"story:{topic}",
            "topic": topic,
        },
    )
    return topic, story, "news"


if __name__ == "__main__":
    t, s, _kind = build_todays_story(
        repo_slug=os.environ.get("REPO_SLUG", "Zed-leo-23/voice-story-narrator"),
        github_token=os.environ["GITHUB_TOKEN"],
    )
    print("TOPIC:", t)
    print(s)
