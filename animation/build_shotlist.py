"""Build animation/stories/<id>.json: every shot with its time, spoken lines and full image prompt.

    python3 animation/build_shotlist.py            # all stories in shots.py
    python3 animation/build_shotlist.py lazy-ox    # one story

Times come from the story's timeline.json on its GitHub Release (story-<id>).
"""
import json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from shots import STORIES  # noqa: E402
from style import CHARACTERS, NEGATIVE, STYLE  # noqa: E402

RELEASE = "https://github.com/Zed-leo-23/voice-story-narrator/releases/download/story-{id}/{name}"
TAG = re.compile(r"^\s*([^\s:：]{1,16})\s*[:：]\s*(.+)$")


def timeline(story_id: str) -> dict:
    local = os.path.join(ROOT, "recordings", story_id, "timeline.json")
    if os.path.exists(local):
        return json.load(open(local, encoding="utf-8"))
    with urllib.request.urlopen(RELEASE.format(id=story_id, name="timeline.json")) as r:
        return json.load(r)


def speakers(story_id: str) -> list[list[str]]:
    """Who says each timeline line, scene by scene (same grouping as narrate.py)."""
    cfg = json.load(open(os.path.join(ROOT, "automation_state", "voices.json"), encoding="utf-8"))
    known = {a.lower() for a in cfg["aliases"]} | {n.lower() for n in cfg["voices"]}
    text = open(os.path.join(ROOT, "automation_state", "scripts", f"{story_id}.txt"), encoding="utf-8").read()
    out = []
    for scene in [s.strip() for s in text.split("\n\n") if s.strip()][1:]:
        who = []
        for line in scene.splitlines():
            m = TAG.match(line)
            name = m.group(1) if m and m.group(1).lower() in known else "해설"
            if not who or who[-1] != name:
                who.append(name)
        out.append(who)
    return out


def build(story_id: str) -> dict:
    plan, tl = STORIES[story_id], timeline(story_id)
    who = speakers(story_id)
    shots = []
    for n, (scene, a, b, picture, motion) in enumerate(plan["shots"], 1):
        lines = tl["scenes"][scene - 1]["lines"]
        names = who[scene - 1]
        assert len(lines) == len(names), f"{story_id} scene {scene}: script and timeline differ"
        cast = [c for c in CHARACTERS if re.search(rf"\b{c}\b", picture)]
        looks = " ".join(f"[{c}] {CHARACTERS[c]}." for c in cast)
        shots.append({
            "shot": n,
            "scene": scene,
            "start": lines[a]["start"],
            # Hold the picture until the next shot starts (covers the pause after the line).
            "end": None,
            "lines": [{"speaker": names[i], "text": lines[i]["text"], "start": lines[i]["start"], "end": lines[i]["end"]}
                      for i in range(a, b + 1)],
            "characters": cast,
            "picture": picture,
            "motion": motion,
            "time": plan.get("times", {}).get(scene),
            "image_prompt": f"{STYLE} Characters: {looks} Scene: {picture}.",
        })
    for cur, nxt in zip(shots, shots[1:]):
        cur["end"] = nxt["start"]
    shots[-1]["end"] = tl["duration"]
    return {
        "id": story_id,
        "title": plan["title"],
        "audio": RELEASE.format(id=story_id, name="full_story.wav"),
        "timeline": RELEASE.format(id=story_id, name="timeline.json"),
        "duration": tl["duration"],
        "style": STYLE,
        "negative_prompt": NEGATIVE,
        "cast": {c: CHARACTERS[c] for c in plan["cast"]},
        "shots": shots,
    }


def main() -> None:
    ids = sys.argv[1:] or list(STORIES)
    os.makedirs(os.path.join(HERE, "stories"), exist_ok=True)
    for story_id in ids:
        data = build(story_id)
        path = os.path.join(HERE, "stories", f"{story_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"{path}: {len(data['shots'])} shots, {data['duration']:.0f}s")


if __name__ == "__main__":
    main()
