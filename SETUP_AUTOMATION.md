# 매일 아침 자동 나레이션 설정 (ScienceDaily → AI 재작성 → 음성 생성 → 카톡 전송)

## 전체 구조

```
GitHub Actions (cron, 매일 새벽)
    │  kaggle kernels push 로 트리거만 함
    ▼
Kaggle 커널 (무료 GPU, 실제 작업 전부 여기서 실행)
    │
    ├─ 1) ScienceDaily RSS에서 오늘의 과학 뉴스 가져오기
    ├─ 2) Claude API로 초등학생용 한국어 대본으로 재작성
    ├─ 3) narrate.py로 내 목소리 클로닝 나레이션 생성
    ├─ 4) 결과 wav를 이 GitHub 저장소의 Release 에셋으로 업로드 (공개 링크 생성)
    └─ 5) 카카오톡 "나에게 보내기"로 그 링크 전송
```

Google Colab 무료 티어는 예약/백그라운드 실행을 지원하지 않아서(유료 기능), 실제 매일 자동
실행은 **Kaggle**(API로 외부에서 트리거 가능한 무료 GPU 노트북)에서 하고, **GitHub Actions**는
그걸 매일 깨우는 알람 역할만 합니다.

제가 코드는 다 만들어뒀지만, 계정/키 설정은 각 서비스 로그인이 필요해서 직접 해주셔야 해요.
아래 순서대로 하나씩 하시면 됩니다. (전부 1회성 설정이고, 그 뒤로는 완전 자동입니다.)

---

## 1. Kaggle 계정 + API 토큰

1. https://www.kaggle.com 가입 (이미 있으면 생략)
2. 우측 상단 프로필 → **Settings** → **API** 섹션 → **Create New Token**
   → `kaggle.json` 파일이 다운로드됩니다 (안에 `username`, `key` 들어있음)
3. 이 저장소 GitHub 페이지 → **Settings → Secrets and variables → Actions → New repository secret**
   으로 아래 두 개 추가:
   - `KAGGLE_USERNAME` = kaggle.json 안의 username
   - `KAGGLE_KEY` = kaggle.json 안의 key

## 2. 내 목소리를 Kaggle Dataset으로 업로드

Kaggle 커널은 GitHub 저장소 파일을 직접 못 읽으니(공개 저장소에 개인 목소리 파일을 올려두는
것도 바람직하지 않고요), 비공개 Kaggle Dataset으로 따로 올려둡니다.

1. https://www.kaggle.com/datasets → **New Dataset**
2. 가지고 계신 레퍼런스 음성 파일(m4a/wav, 아무 길이나 — 엔진이 자동으로 3~10초 구간을 골라줌)을 업로드
3. **Private**로 설정하고 생성 (예: 데이터셋 이름 `my-voice-reference`)
4. 생성된 데이터셋 주소에서 `kaggle-username/my-voice-reference` 형태의 slug를 확인

## 3. `kaggle_kernel/kernel-metadata.json` 수정

이 파일을 열어서 `YOUR_KAGGLE_USERNAME`을 실제 Kaggle 사용자명으로, 데이터셋 경로를 2번에서
만든 slug로 바꿔주세요.

```json
{
  "id": "실제유저명/daily-science-narration",
  ...
  "dataset_sources": ["실제유저명/my-voice-reference"]
}
```

고치신 뒤 커밋/푸시해주시면 제가 이어서 확인할게요.

## 4. Anthropic(Claude) API 키

1. https://console.anthropic.com → **API Keys** → 새 키 생성
2. 과학 기사 재작성에 쓰이는데, 하루 한 번 짧은 글 하나 생성하는 수준이라 비용은 거의 안 듭니다
   (하루 몇 센트 수준).

이 키는 GitHub Secret이 아니라 **Kaggle 커널 Secret**으로 등록합니다 (바로 아래 6번에서 한 번에 설정).

## 5. GitHub Personal Access Token (커널이 Release 업로드용으로 사용)

1. GitHub → **Settings → Developer settings → Fine-grained personal access tokens → Generate new token**
2. **Repository access**: 이 저장소(`voice-story-narrator`)만 선택
3. **Permissions → Contents**: Read and write
4. 생성된 토큰을 복사해두세요 (한 번만 보여줍니다)

이것도 Kaggle 커널 Secret으로 등록합니다.

## 6. Kaggle 커널 Secrets 등록

1. 아래 "7. 최초 1회 수동 실행"을 먼저 해서 커널을 한 번 만드세요 (Secrets는 커널이 존재해야 등록 가능)
2. https://www.kaggle.com/code/실제유저명/daily-science-narration 접속 → **Edit**
3. 우측 **Add-ons → Secrets**
4. 아래 4개를 각각 추가 (Label = 환경변수 이름과 동일하게, Attach 체크):
   - `ANTHROPIC_API_KEY` = 4번에서 만든 키
   - `GITHUB_TOKEN` = 5번에서 만든 토큰
   - `KAKAO_REST_API_KEY` = 아래 7번에서 만든 카카오 REST API 키
   - `KAKAO_REFRESH_TOKEN` = 아래 7번에서 발급받은 refresh token

## 7. 카카오톡 "나에게 보내기" 설정 (가장 번거로운 부분, 최초 1회만)

1. https://developers.kakao.com → 로그인 → **내 애플리케이션 → 애플리케이션 추가**
2. 앱 이름 아무거나 (예: "과학 나레이션 알림")
3. 생성된 앱 → **요약 정보**에서 **REST API 키** 복사해두기 (이게 `KAKAO_REST_API_KEY`)
4. **제품 설정 → 카카오 로그인 → 활성화 ON**
5. 같은 화면 **Redirect URI**에 아무 URL이나 하나 등록 (예: `https://localhost:3000`) — 실제로
   그 주소가 동작할 필요는 없고, 인증 과정에서 리다이렉트만 받을 용도입니다.
6. **제품 설정 → 카카오 로그인 → 동의항목**에서 **카카오톡 메시지 전송** (`talk_message`) 항목을
   "선택 동의" 또는 "필수 동의"로 설정
7. 브라우저 주소창에 아래 URL을 `{REST_API_KEY}`와 `{REDIRECT_URI}`를 실제 값으로 바꿔서 접속:

   ```
   https://kauth.kakao.com/oauth/authorize?client_id={REST_API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code&scope=talk_message
   ```

8. 카카오 로그인 후 동의 화면에서 허용 → `{REDIRECT_URI}?code=XXXXXXXX` 형태로 리다이렉트됨
   (페이지가 안 뜰 수 있는데 괜찮습니다, 주소창의 `code=` 뒤 값만 복사하면 됩니다)
9. 터미널에서 아래 실행 (역시 값들을 실제 값으로 치환):

   ```bash
   curl -X POST https://kauth.kakao.com/oauth/token \
     -d grant_type=authorization_code \
     -d client_id={REST_API_KEY} \
     -d redirect_uri={REDIRECT_URI} \
     -d code={위에서 복사한 code}
   ```

10. 응답 JSON의 `refresh_token` 값을 복사 → 이게 `KAKAO_REFRESH_TOKEN` (6번에서 Kaggle Secret으로 등록)

refresh_token은 보통 두 달 정도 유효합니다. 만료되면 7~9번 과정을 다시 한 번 해주셔야 해요
(나중에 자동 재발급까지 필요하시면 말씀해주세요, 추가로 구성해드릴 수 있어요).

## 8. 최초 1회 수동 실행 (커널 생성 + 테스트)

로컬 터미널이나 이 환경에서:

```bash
pip install kaggle
export KAGGLE_USERNAME=...
export KAGGLE_KEY=...
kaggle kernels push -p kaggle_kernel/
```

커널 페이지(`https://www.kaggle.com/code/실제유저명/daily-science-narration`)에서 실행 로그를
확인하세요. Secrets를 다 등록하기 전까지는 실패하는 게 정상이니, 에러 메시지 보면서 하나씩
채워나가면 됩니다. 끝까지 성공하면 카카오톡으로 메시지가 와야 합니다.

## 9. GitHub Actions 스케줄 확인

`.github/workflows/daily-kaggle-trigger.yml`이 매일 UTC 19:00(한국시간 새벽 4시)에 자동으로
`kaggle kernels push`를 실행합니다. 시간을 바꾸고 싶으면 그 파일의 `cron` 값을 수정하세요.
GitHub 저장소 **Actions** 탭에서 **Run workflow** 버튼으로 수동 테스트도 가능합니다
(workflow_dispatch로 설정해뒀습니다).
