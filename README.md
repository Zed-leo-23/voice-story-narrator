# voice-story-narrator

내 목소리를 녹음해서 동화(또는 어떤 텍스트든) 전체를 그 목소리로 자동 나레이션하는 파이프라인입니다.
무료 Google Colab GPU에서 돌아가도록 구성했습니다.

음성 엔진은 [VoiceStudio](https://github.com/debpalash/voicestudio)에 번들된 로컬 TTS 모델
**OmniVoice**(k2-fsa/OmniVoice, Apache-2.0)를 사용합니다. 엔진 소스는 이 저장소에 복사해 넣지 않고,
실행할 때마다 `debpalash/voicestudio`를 그대로 클론해서 씁니다(최신 업스트림 유지, 라이선스 중복 배포 방지).

이 저장소에는 오케스트레이션 코드(`narrate.py`)와 Colab 노트북, 예시 동화만 들어 있습니다.

## 빠른 시작 (Google Colab)

1. [`notebooks/narrate_colab.ipynb`](notebooks/narrate_colab.ipynb)를 Colab에서 엽니다.
2. **런타임 > 런타임 유형 변경 > 하드웨어 가속기: GPU(T4)** 선택 후 저장.
3. 셀을 순서대로 실행합니다.
4. 3번째 셀에서 **내 목소리 녹음 파일**(wav, 3~10초 구간 권장. 더 길어도 업로드는 가능)을 업로드합니다.
5. 4번째 셀의 `REF_TEXT`: 녹음을 3~10초로 직접 맞췄다면 그 문장을 정확히 입력하고, 그게 번거로우면
   그냥 빈 문자열(`""`)로 두세요 — 엔진이 녹음 중에서 적당한 짧은 구간을 알아서 골라 음색을 추출합니다.
6. 5번째 셀: 처음엔 포함된 예시 동화(`examples/story.txt`, 옥토넛+원피스+닌자고 크로스오버)로 테스트하거나,
   내 동화 파일을 업로드해서 써도 됩니다.
7. 결과는 Google Drive의 `MyDrive/voice-story-narrator/output/`에 장면별 wav + 합쳐진 `full_story.wav`로 저장됩니다.

## 좋은 레퍼런스 녹음 만드는 법

- **길이: 3~10초**가 실제로 쓰이는 구간입니다. 녹음 자체는 더 길게 해도 되지만(예: 20~30초),
  `REF_TEXT`를 비워두면 엔진이 그중 3~10초짜리 좋은 구간을 알아서 골라 음색을 추출합니다.
  직접 구간을 맞추고 싶다면 오디오를 3~10초로 잘라서 올리고, `REF_TEXT`에 그 구간 대본만 입력하세요.
  (레퍼런스 오디오가 너무 길면 `[clone_ref_too_long]` 에러가 납니다.)
- 조용한 곳에서, 마이크와 일정한 거리를 유지하고 녹음하세요. 배경 잡음/에코가 적을수록 결과가 좋습니다.
- 평소 말하는 속도와 톤으로 자연스럽게 읽으세요 (너무 또박또박 느리게 읽으면 오히려 어색해집니다).
- `REF_TEXT`를 직접 입력할 경우, 녹음에서 실제로 말한 문장과 토씨 하나까지 정확히 일치해야 합니다.

## 로컬/다른 환경에서 직접 실행하기

```bash
git clone --depth 1 https://github.com/debpalash/voicestudio
export PYTHONPATH=$PWD/voicestudio
pip install -r requirements.txt   # GPU torch가 이미 있다면 그대로, 없다면 torch/torchaudio도 추가 설치

python narrate.py \
  --story examples/story.txt \
  --ref_audio my_voice.wav \
  --language Korean \
  --outdir output
# --ref_text는 선택사항입니다. 녹음을 3~10초로 직접 맞췄다면
# --ref_text "레퍼런스 녹음 대본 그대로" 를 추가하세요.
```

## 동화 텍스트 포맷

`narrate.py`는 **빈 줄로 구분된 문단을 각각 하나의 장면(scene)**으로 봅니다. 장면마다 따로 생성한 뒤
장면 사이에 짧은 무음(`--gap_seconds`, 기본 0.6초)을 넣어 이어붙입니다. 장면별 wav도 `scene_01.wav`,
`scene_02.wav` ... 형태로 `--outdir`에 함께 저장되니, 특정 장면만 다시 만들고 싶을 때 유용합니다.

## 주요 옵션 (`narrate.py`)

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--num_step` | 32 | 생성 스텝 수. 높일수록 품질↑ 속도↓ |
| `--guidance_scale` | 2.0 | 레퍼런스 음색을 얼마나 강하게 따라갈지 |
| `--speed` | 1.0 | 말하는 속도 |
| `--gap_seconds` | 0.6 | 장면 사이 무음 길이(초) |
| `--language` | Korean | 생성 언어 |

## 알아두면 좋은 점

- Colab 무료 플랜은 GPU를 **무기한 보장하지 않습니다** — 혼잡 시 배정이 안 되거나, 일정 시간/사용량 넘으면
  런타임이 끊길 수 있습니다. 긴 동화는 장면 단위로 나눠서(`narrate.py`가 이미 장면별로 저장하므로) 중간에
  끊겨도 이어서 진행할 수 있게 설계했습니다.
- Colab 세션 저장공간(`/content`)은 세션 종료 시 사라집니다. 결과물은 반드시 Google Drive(`/content/drive/...`)
  경로에 저장하세요 (노트북에 이미 그렇게 설정돼 있습니다).
- 음성 클로닝은 본인 동의 하에 본인 목소리로만 사용하세요.
