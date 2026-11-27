# 엉뚱한 동화극장: 유튜브 자동 업로드 파이프라인 (인계 문서)

이 문서는 다른 Claude Code 세션(사용자 컴퓨터 등)에서 이어서 작업할 수 있도록,
지금까지 만든 것과 앞으로 만들 것을 정리한 것이다. 새 세션은 이 문서부터 읽는다.

## 목표 흐름

```
동화 대본 생성 → 녹음 → 영상 → 오디오 싱크 → 중간 효과음 → 검수 → 유튜브 자동 업로드
```

## 1. 이미 있는 것 (이 저장소)

| 단계 | 상태 | 어디에 |
|---|---|---|
| 동화 대본 | ✅ 사람이 고른 민담을 우리 말로 새로 쓴 대본 | `automation_state/scripts/*.txt` |
| 녹음 | ✅ Kaggle 무료 GPU에서 OmniVoice로 생성 | `narrate.py`, `scripts/daily_pipeline.py` |
| 녹음 결과 | ✅ GitHub Release에 올라감 | 태그 `story-<파일이름>` (예: `story-samani`) |
| 장면·대사 시간표 | ✅ 오디오와 같은 Release에 `timeline.json` | 아래 형식 참고 |
| 카톡 알림 | ✅ 완성되면 링크 전송 | `scripts/kakao.py` |
| 영상, 효과음, 검수, 유튜브 | ❌ 앞으로 만들 것 | 아래 2~6장 |

### 대본 형식

```
주제: 삼년고개
목소리: reviewer

엉뚱한 동화극장, 오늘의 이야기는 …   ← 장면은 빈 줄로 구분, 태그 없는 줄은 해설
할아버지: 아이고, 벌써 해가 지네.      ← "이름: 대사" 는 캐릭터 목소리
…
엉뚱한 동화극장, 다음에 또 만나요~
```

- 이름 → 목소리 연결은 `automation_state/voices.json` 의 `aliases`
  (예: 할아버지→아빠, 꼬마→owner, 괴물→devil, 까치→dole).
- 목소리 녹음 파일은 Kaggle 데이터셋 `raon07/dochi-1-minwoo-ver2`
  (Father, owner, devil, fun ver voice, dole 2). **엄마(yk voice)는 쓰지 않는다.**
- 대본은 **전래 민담을 우리 말로 새로 쓴 것만** 쓴다. 다른 채널·책의 대본을 베끼지 않는다.
- 후보 목록(1~92번)은 대화 기록에 있음. 완성: 71 이야기 주머니, 72 삼년고개, 73~76.

### 녹음 실행 방법

```bash
gh api -X POST repos/Zed-leo-23/voice-story-narrator/actions/workflows/daily-kaggle-trigger.yml/dispatches \
  -f ref=main -f 'inputs[story]=samani.txt,bird-talk.txt'
```

- **main에 합치지 않고 녹음하기**: 새 대본을 따로 브랜치(예: `story/folktales-2`)에 올리고
  `-f ref=<그 브랜치>` 로 실행하면, Kaggle이 그 브랜치를 클론해서 녹음한다.
  매일 아침 뉴스(스케줄 실행)는 계속 main을 쓴다. 다 확인한 대본만 나중에 main에 합치면 된다.
- 실행 확인: Kaggle이 실제로 시작하면 `Update topic history` 커밋이 생긴다.
- 실패하면 `automation_state/run_logs/last_error.txt` 에 오류와 로그 끝부분이 저장된다
  (`Run error: …` 커밋).
- Kaggle 무료 GPU 대기열이 자주 멈춘다(Starting/Queued). 15분 넘게 안 시작하면
  Kaggle 화면에서 그 버전을 Cancel 하고 다시 실행.
- 목소리 엔진(voicestudio)은 `kaggle_kernel/daily-science-narration.py` 의
  `ENGINE_COMMIT` 으로 고정돼 있다. 업스트림 최신 버전은 2026-11-22에 모델 로딩이 깨졌다.

### 결과물 받기

```bash
gh api repos/Zed-leo-23/voice-story-narrator/releases/tags/story-samani \
  --jq '.assets[] | [.name, .id] | @tsv'
gh api -H "Accept: application/octet-stream" \
  repos/Zed-leo-23/voice-story-narrator/releases/assets/<id> > full_story.wav
```

### timeline.json 형식 (영상 싱크의 기준)

```json
{"duration": 304.0,
 "scenes": [
  {"scene": 1, "start": 0.0, "end": 14.6,
   "lines": [{"voice": "reviewer", "text": "엉뚱한 동화극장, …", "start": 0.0, "end": 14.6}]},
  {"scene": 2, "start": 15.5, "end": 37.2, "lines": [ … ]}
 ]}
```

- 시간은 `full_story.wav` 기준 초 단위. 장면 사이는 0.9초, 대사 사이는 0.4초가 비어 있다.
- 마지막 인사 뒤 2초는 여운(무음)이다.
- **2026-11-22 이후에 만든 녹음에만 있다.** 그 전 것(71·72)은 다시 녹음하면 생긴다.

## 2. 영상 만들기 (추천 방식)

장면마다 그림 한 장 + 천천히 움직이는 효과(Ken Burns) + 자막이면 충분하다.

1. **장면 그림**: `timeline.json` 의 장면마다 그림 1장.
   - AI 이미지 생성 API를 쓰거나, 직접 그린 그림을 폴더에 넣는다.
   - 화풍을 고정하려면 프롬프트 앞부분을 공통으로(예: "따뜻한 수채화풍 한국 전래동화 그림책")
     정하고, 캐릭터 설명도 고정한다.
   - 실존 캐릭터·다른 채널 그림을 흉내 내지 않는다.
2. **영상 합성**: `ffmpeg` 로 장면 그림을 `start~end` 길이만큼 보여주고(zoompan),
   `full_story.wav` 를 붙인다. 1920×1080, 30fps.
3. **자막**: `timeline.json` 의 `lines` 로 SRT를 만든다. 긴 대사는 문장 단위로 쪼개서
   대사 시간 안에서 글자 수 비율로 나눈다. 영상에 굽거나(burn-in) 유튜브에 따로 올린다.
4. **썸네일**: 제목 글자 + 대표 장면 그림, 1280×720.

## 3. 효과음

- **저작권 걱정 없는 것만**: YouTube 오디오 보관함, CC0(퍼블릭 도메인) 효과음.
  출처와 라이선스를 `assets/sfx/LICENSES.md` 에 적어 둔다.
- 대본에 표시를 넣어서 자동으로 배치하는 방식 추천:
  `[효과: 문 열림]` 같은 줄을 대본에 넣고, 녹음에서는 읽지 않게 하고(narrate에서 무시 처리
  필요), 영상 단계에서 그 위치(timeline)에 효과음을 섞는다.
- 효과음은 목소리보다 작게(-18 dB 정도), 대사와 겹치면 더 줄인다(ducking).
- 배경음악을 깐다면 아주 작게(-28 dB 정도).

## 4. 검수 (자동 + 사람)

자동 검사는 이미 녹음 단계에 있다(받아쓰기로 군더더기·빠진 말·속삭임·삐이잉 검사).
영상 단계에서 더할 것:

- 영상 길이 = 오디오 길이, 소리 크기(-14 LUFS 근처), 무음 구간이 너무 긴 곳이 없는지.
- **사람 검수는 꼭 남긴다**: 완성 영상 링크를 카톡으로 보내고, 사용자가 "올려"라고 해야
  업로드. (아이 채널은 사고 한 번이 치명적이다.)

## 5. 유튜브 자동 업로드

- **YouTube Data API v3** 로 업로드한다.
  - Google Cloud 프로젝트 → YouTube Data API v3 사용 설정 → OAuth 동의 화면 →
    OAuth 클라이언트(데스크톱 앱) → 한 번 로그인해서 **refresh token** 을 받는다.
  - 토큰·클라이언트 비밀은 GitHub Secrets 에만 저장한다. 채팅·코드에 넣지 않는다.
- **꼭 알아야 할 제한**
  - 검증(audit) 안 된 API 프로젝트로 올린 영상은 **비공개로만** 올라간다.
    처음에는 비공개로 올리고 유튜브 스튜디오에서 직접 공개로 바꾸거나,
    Google에 API 감사(audit)를 신청해야 공개 업로드가 된다.
  - 하루 할당량 10,000 유닛, 업로드 1건 ≈ 1,600 유닛 → 하루 최대 약 6편.
- **아이용 채널 설정**
  - 업로드 시 `selfDeclaredMadeForKids: true` (아동용으로 지정). 댓글·맞춤 광고가 꺼진다.
  - AI 목소리를 쓰므로 "변경되거나 합성된 콘텐츠" 공개 항목을 켠다(`containsSyntheticMedia`).
- 제목 형식: `가난한 과부와 수상한 외상 손님 (…) | 엉뚱한 동화극장 | 민담 · 설화 · 옛날이야기`
  다른 채널 이름을 제목·태그에 넣지 않는다.

## 6. 어디서 돌릴지

| 단계 | 추천 장소 | 이유 |
|---|---|---|
| 녹음 | Kaggle (지금처럼) | 무료 GPU. 대기열 멈춤이 잦으면 유료 GPU(Colab Pro, RunPod) 고려 |
| 영상·효과음·자막 | GitHub Actions 또는 사용자 컴퓨터 | GPU 불필요, ffmpeg만 있으면 됨 |
| 검수 | 카톡 링크 + 사용자 승인 | |
| 업로드 | GitHub Actions (승인 후 수동 실행) | 토큰을 Secrets에 안전하게 보관 |

추천 연결: 녹음 Release가 올라오면 → 영상 워크플로(Actions)가 자동 실행 →
영상을 Release에 올리고 카톡으로 미리보기 → 사용자가 승인하면 업로드 워크플로 실행.

## 7. 새 세션에서 할 일 (순서)

1. 이 저장소를 클론하고 `docs/youtube-pipeline.md` 를 읽는다.
2. `ffmpeg`, Python 3.11+, `gh` 로그인 확인.
3. 이미 녹음된 Release 하나(예: `story-samani`)의 `full_story.wav` + `timeline.json` 으로
   **영상 만들기 스크립트**(`video/make_video.py`)부터 만든다. 그림은 처음엔 단색 배경 +
   장면 제목 글자로 시작해도 된다.
4. 자막(SRT) → 효과음 표시 → 썸네일 순서로 붙인다.
5. YouTube API OAuth 설정(사용자가 직접 Google Cloud에서 진행) 후 업로드 스크립트,
   처음엔 **비공개**로 한 편 올려서 확인.
6. GitHub Actions 워크플로로 묶는다: 녹음 완료 → 영상 → 카톡 미리보기 → 승인 → 업로드.
