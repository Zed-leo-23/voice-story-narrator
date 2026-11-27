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

**정한 그림체 (2026-11-27, 두 번째):** 단순한 한국 웹툰풍 유튜브 민담 만화.
- 굵은 검정 외곽선, 그림자·그라데이션 없는 단색, 몇 가지 차분한 색만 써요.
- 큰 둥근 머리, 작은 점 눈, 분명한 표정이에요.
- 배경은 장면에 필요한 벽·문·바닥·언덕 정도만 단순한 면으로 그려요.
- 조선 배경(초가, 한옥, 한복)이에요.
- SDXL에서는 `flat` 룩(flat illustration LoRA)이 기본이에요. 처음 정했던 셀 애니메이션 + 과슈 배경은 `gouache_90s` 룩으로 남아 있어요.
- 사용자가 보여 준 레퍼런스는 **분위기 참고용**이에요. 그 채널·작품의 캐릭터를 따라 그리지 않고,
  남의 화면을 저장소에 올리거나 참고 이미지로 넣지 않아요.
  대신 우리가 그린 그림 중 마음에 드는 것을 `reference/` 기준 그림으로 써요.


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
5. 그림 안에 글자·말풍선을 넣지 않는다(자막은 따로 붙인다). 일본 오니·기모노로 그리지 않는다(배경은 조선).
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
| SDXL 모델·크기·단계 수 | `render_cuts.py` |

고친 뒤 `python3 animation/build_shotlist.py` 로 `stories/*.json` 을 다시 만든다.
새 이야기를 추가하면 `shots.py` 에 같은 모양으로 넣는다(장면·대사 번호는 그 이야기의 `timeline.json` 순서, 0부터).

## 5. Kaggle 무료 GPU로 컷 그리기 (SDXL, 오픈소스)

Gemini 대신 Kaggle 무료 GPU에서 SDXL로 샷 그림을 그린다. API 요금이 없다.

| 파일 | 하는 일 |
|---|---|
| `animation/render_cuts.py` | 샷 목록을 읽어 샷마다 그림 1장(1920×1080)을 그린다 |
| `kaggle_animation/` | Kaggle 노트북 `raon07/story-animation-cuts`. 저장소를 받아 위 스크립트를 돌리고 결과를 올린다 |
| `.github/workflows/animation-kaggle.yml` | 수동 실행 버튼. Kaggle에 노트북을 올려 실행시킨다 |

**실행:** GitHub → Actions → *Draw animation cuts on Kaggle* → Run workflow
→ 브랜치 선택, `story`(예: `tiger-persimmon`), 필요하면 `shots`(예: `1,2,3`) 입력.
처음엔 `shots` 에 `1,2` 처럼 몇 장만 넣어 그림체를 먼저 본다.

**결과:** 15~30분 뒤 GitHub Release `cuts-<id>` 에 올라온다.
`contact_sheet.jpg`(한눈에 보기), `shot_01.png`…, 전체 묶음 zip, 사용한 프롬프트 `prompts.json`.
실패하면 Kaggle 노트북 페이지의 로그를 본다.

**필요한 GitHub Secrets**
- `RELEASE_PAT`: 저장소 받기·Release 올리기 (이미 있음)
- `KAGGLE_API_TOKEN`: 매일 도는 낭독과 같은 Kaggle 계정(raon07) 토큰 (이미 있음).
  주당 무료 GPU 시간(약 30시간)을 낭독과 함께 쓴다. 낭독은 하루 10분 정도라 여유가 있다.

### 배경과 캐릭터를 따로 그리는 방식 (기본, `render_layered.py`)

한 장에 장면 전체를 그리면 호랑이가 빠지거나 다른 동물과 섞이고, 컷마다 생김새가 달라졌다.
그래서 따로 그려서 합친다.

1. **배경**: 인물 없이 장소만 그린다 (`layers.py` 의 `backgrounds`). 여러 컷이 같은 배경을 다시 쓴다.
2. **캐릭터**: 흰 배경에 한 동작씩 그린다 (`sprites`). 캐릭터마다 첫 그림이 기준 그림이고,
   나머지 동작은 IP-Adapter로 그 기준 그림을 참고해서 생김새를 맞춘다.
   흰 배경은 rembg(애니 모델)로 지우고, 안 되면 가장자리부터 흰색을 지운다.
3. **합치기**: 컷마다 배경 위에 캐릭터를 놓는다 (`shots`: 위치·크기·좌우 반전). 밤이면 캐릭터를 살짝 어둡게 한다.

결과: `shot_XX.png`, `layers/`(배경·캐릭터 원본), `layout.json`(나중에 캐릭터만 움직이는 애니메이션에 쓴다).
Actions 실행 화면의 `mode` 를 `single` 로 하면 예전 방식(한 장에 전부)으로 그린다.

**그림 바꾸기:** 같은 seed + 같은 프롬프트 = 같은 그림. 그림체는 `style.py` 를 고친다.
SDXL은 한국어를 못 읽어서 `render_cuts.py` 가 캐릭터 이름표(`호랑이:`)를 빼고
장면 → 캐릭터 외형 → 그림체 순서로 프롬프트를 다시 만든다. 미리 보기:
`python3 animation/render_cuts.py tiger-persimmon --dry-run` (GPU 필요 없음).

## 6. 주의

- Gemini API 키는 채팅이나 코드에 넣지 않는다. 환경 변수 또는 GitHub Secrets(`GEMINI_API_KEY`)에만 둔다.
- 완성 영상은 유튜브에 올리기 전에 반드시 사람이 본다(`docs/youtube-pipeline.md` 4장).
- AI로 만든 그림·목소리이므로 업로드할 때 "변경되거나 합성된 콘텐츠"를 켠다.

## 7. 새 세션 첫 메시지 예시

```
https://github.com/Zed-leo-23/voice-story-narrator 저장소의
claude/confident-planck-hh11y6 브랜치에서 animation/README.md 를 읽고,
기준 그림체를 확인한 다음 tiger-persimmon 부터 샷 그림을 Gemini로 만들어줘.
```
