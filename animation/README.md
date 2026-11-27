# 민담 애니메이션 만들기 (인계 문서)

녹음이 끝난 민담을 **대사에 맞춘 그림 애니메이션**으로 만드는 작업이다.
그림은 Gemini로 그리고, **모든 이야기의 그림체가 똑같아야 한다.**
새 세션은 이 문서부터 읽는다.

## 1. 지금 있는 것

| 이야기 | 샷 목록 | 길이 |
|---|---|---|
| 혹부리 영감과 노래 주머니 | `stories/hump-old-man.json` | 3분 43초, 13샷 |
| 간을 두고 온 토끼 | `stories/rabbit-liver.json` | 3분 36초, 14샷 |
| 소가 된 게으름뱅이 | `stories/lazy-ox.json` | 3분 43초, 14샷 |
| 바닷물이 짠 까닭 | `stories/salt-millstone.json` | 3분 33초, 12샷 |
| 호랑이보다 무서운 곶감 | `stories/tiger-persimmon.json` | 3분 57초, 14샷 |

- 녹음(`full_story.wav`)과 시간표(`timeline.json`)는 GitHub Release `story-<id>` 에 있다.
  각 샷 목록 JSON의 `audio`, `timeline` 에 내려받기 주소가 들어 있다.
- 대본은 `automation_state/scripts/<id>.txt`.
- 이 다섯 편은 `main` 이 아니라 작업 브랜치(`claude/confident-planck-hh11y6`)에 있다.
  새 세션은 이 브랜치를 체크아웃해서 시작한다.

### 샷 목록 JSON 한 칸의 뜻

```json
{
  "shot": 5, "scene": 3,
  "start": 78.37, "end": 93.11,          ← 이 그림이 화면에 나오는 시간(초, full_story.wav 기준)
  "lines": [{"speaker": "혹부리영감", "text": "그, 그건 말이야…", "start": 85.83, "end": 92.71}],
  "characters": ["hump_man", "goblin_chief"],
  "picture": "장면 설명(영어)",
  "motion": "slow zoom on the lump",      ← 움직임(영상 만들 때 쓰는 지시)
  "image_prompt": "그림체 + 등장인물 외형 + 장면 — 이것을 그대로 Gemini에 넣는다"
}
```

- `end` 는 다음 샷 `start` 까지라서, 샷을 이어 붙이면 오디오 길이와 딱 맞는다.
- `lines` 는 그 샷 동안 나오는 대사다. 자막과 입 모양 타이밍에 쓴다.
- JSON 맨 위의 `negative_prompt` 는 "이런 건 그리지 마" 목록이다. 지원하는 도구면 함께 넣는다.

## 2. 그림체를 똑같이 유지하는 방법 (가장 중요)

1. **기준 그림을 먼저 정한다.**
   - 다른 세션에서 Gemini로 이미 그린 그림이 있으면 그것이 기준이다.
     `animation/reference/` 폴더에 넣고(예: `reference/style_01.png`), 아래 3번처럼 쓴다.
   - 그 그림체가 `style.py` 의 `STYLE` 문장과 다르면, `STYLE` 을 기준 그림에 맞게 고치고
     `python3 animation/build_shotlist.py` 를 다시 돌린다. 모든 샷의 프롬프트가 한 번에 바뀐다.
2. **캐릭터 설정 그림을 먼저 그린다.** 캐릭터마다 한 장씩 그린다(정면·옆모습·표정 3개, 흰 배경).
   프롬프트는 `STYLE` + `style.py` 의 그 캐릭터 설명 + "character reference sheet, front and side view,
   three expressions, plain white background". 마음에 드는 것을 `reference/<캐릭터키>.png` 로 저장한다.
3. **샷을 그릴 때마다 참고 그림을 같이 넣는다.**
   `image_prompt` 와 함께, 그 샷 `characters` 의 설정 그림 + 기준 그림체 한 장을 참고 이미지로 넣는다.
   Gemini 이미지 생성은 참고 이미지를 여러 장 받을 수 있다.
4. **바꾸지 말 것**: 혹의 위치(혹부리 영감=오른쪽 볼, 욕심 영감=왼쪽 볼, 나중엔 양쪽), 옷 색, 도깨비 뿔 개수.
   이런 차이가 그림마다 달라지면 아이들이 바로 알아챈다.
5. 그림 안에 글자·말풍선을 넣지 않는다(자막은 따로 붙인다). 일본 오니처럼 그리지 않는다.
   다른 채널·만화의 캐릭터를 흉내 내지 않는다.

## 3. 애니메이션 만드는 순서

1. 샷마다 그림 1장 (16:9, 1920×1080 이상) → `animation/out/<id>/shot_05.png`
2. 움직임 넣기 — 둘 중 하나
   - **Gemini 영상(Veo, 이미지→영상)**: 샷 그림 + `motion` + 장면 설명으로 짧은 클립을 만든다.
     클립이 샷 길이보다 짧으면 마지막 프레임을 멈추거나 천천히 확대해서 채운다.
     **클립 소리는 끄고**, 소리는 반드시 `full_story.wav` 하나만 쓴다(싱크 기준).
   - **간단 버전(Ken Burns)**: ffmpeg `zoompan` 으로 그림을 `end-start` 초 동안 천천히 움직인다. 무료·빠름.
3. 샷 클립을 순서대로 이어 붙이고 `full_story.wav` 를 깐다. 30fps.
4. 자막: `lines` 로 SRT를 만든다. 긴 해설은 문장 단위로 나눠 글자 수 비율로 시간을 나눈다.
5. 확인: 영상 길이 = 오디오 길이, 샷 바뀌는 순간이 대사 시작과 맞는지 처음·중간·끝을 본다.

## 4. 고치는 곳

| 바꾸고 싶은 것 | 고칠 파일 |
|---|---|
| 그림체 | `style.py` 의 `STYLE`, `NEGATIVE` |
| 캐릭터 외형 | `style.py` 의 `CHARACTERS` |
| 샷 나누기·장면 내용·움직임 | `shots.py` |

고친 뒤 `python3 animation/build_shotlist.py` 로 `stories/*.json` 을 다시 만든다.
새 이야기를 추가하면 `shots.py` 에 같은 모양으로 넣는다(장면·대사 번호는 그 이야기의 `timeline.json` 순서, 0부터).

## 5. 주의

- Gemini API 키는 채팅이나 코드에 넣지 않는다. 환경 변수 또는 GitHub Secrets(`GEMINI_API_KEY`)에만 둔다.
- 완성 영상은 유튜브에 올리기 전에 반드시 사람이 본다(`docs/youtube-pipeline.md` 4장).
- AI로 만든 그림·목소리이므로 업로드할 때 "변경되거나 합성된 콘텐츠"를 켠다.

## 6. 새 세션 첫 메시지 예시

```
https://github.com/Zed-leo-23/voice-story-narrator 저장소의
claude/confident-planck-hh11y6 브랜치에서 animation/README.md 를 읽고,
기준 그림체를 확인한 다음 tiger-persimmon 부터 샷 그림을 Gemini로 만들어줘.
```
