"""Science-news RSS feeds from several outlets, merged into one candidate
pool. A feed that's down or malformed is skipped, not fatal -- one bad
outlet shouldn't cost the whole morning's narration.
"""

import re
import xml.etree.ElementTree as ET

import requests

# (name read aloud in the narration, feed url)
FEEDS = [
    ("사이언스 뉴스 익스플로어스", "https://www.snexplores.org/feed"),
    ("사이언스 뉴스 익스플로어스", "https://www.snexplores.org/topic/tech/feed"),
    ("스미소니언 매거진", "https://www.smithsonianmag.com/rss/innovation/"),
    ("사이언스데일리", "https://www.sciencedaily.com/rss/computers_math/robotics.xml"),
    ("미국항공우주국 나사", "https://www.nasa.gov/news-release/feed/"),
    ("스미소니언 매거진", "https://www.smithsonianmag.com/rss/smartnews-science/"),
    ("라이브 사이언스", "https://www.livescience.com/feeds/all"),
    ("사이언스 뉴스", "https://www.sciencenews.org/feed"),
    ("사이언스데일리", "https://www.sciencedaily.com/rss/plants_animals.xml"),
    ("사이언스데일리", "https://www.sciencedaily.com/rss/space_time.xml"),
    ("사이언스데일리", "https://www.sciencedaily.com/rss/fossils_ruins.xml"),
    ("한겨레", "https://www.hani.co.kr/rss/science/"),
    ("경향신문", "https://www.khan.co.kr/rss/rssdata/science_news.xml"),
]

_TAG = re.compile(r"<[^<]+?>")
_UA = {"User-Agent": "Mozilla/5.0 (compatible; voice-story-narrator/1.0)"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", text or "")).strip()


def fetch_feed(source: str, url: str, limit: int) -> list[dict]:
    resp = requests.get(url, headers=_UA, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        title = _clean(item.findtext("title"))
        if not link or not title:
            continue
        items.append(
            {
                "source": source,
                "title": title,
                "description": _clean(item.findtext("description"))[:400],
                "link": link,
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch_all_candidates(per_feed_limit: int = 8) -> list[dict]:
    seen: set[str] = set()
    pool: list[dict] = []
    for source, url in FEEDS:
        try:
            items = fetch_feed(source, url, per_feed_limit)
        except Exception as exc:  # noqa: BLE001 -- any feed failure just drops that feed
            print(f"skipping feed {url}: {exc}")
            continue
        for it in items:
            if it["link"] not in seen:
                seen.add(it["link"])
                pool.append(it)
    print(f"collected {len(pool)} candidate articles from {len(FEEDS)} feeds")
    return pool
