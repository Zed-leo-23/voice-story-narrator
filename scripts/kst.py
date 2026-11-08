"""The pipeline runs on Kaggle's servers (UTC), but "today" for a daily
Korean-morning narration should mean the Korean calendar day, not UTC's
-- otherwise dates in the Release tag/title, KakaoTalk text, and topic
history drift by a day for part of each 24h cycle.
"""

import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def today() -> datetime.date:
    return datetime.datetime.now(KST).date()
