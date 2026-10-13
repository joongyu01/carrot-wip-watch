# carrot-wip-watch

5분마다 `ajouatom/openpilot`의 `carrot-wip`에 새 커밋이 있는지 보고, 있으면 텔레그램으로 알려준다.
커밋 목록, 바뀐 영역, capnp 변경과 `joongyu01/carrot-wip-dev`와 겹치는 파일, Gemini(3.8 Flash)가 쓴 한국어 변경 요약을 보낸다.

## 설정 (Settings → Secrets and variables → Actions → New repository secret)
- `TELEGRAM_BOT_TOKEN`: @BotFather가 준 봇 토큰
- `TELEGRAM_CHAT_ID`: 봇에 메시지를 한 번 보낸 뒤 `https://api.telegram.org/bot<토큰>/getUpdates`에서 `"chat":{"id": ...}` 값
- `GEMINI_API_KEY` (선택): 없으면 AI 요약 없이 목록만 보낸다

`last_sha.txt`는 마지막으로 알린 커밋이다. Actions 탭의 "Run workflow"로 바로 실행해 볼 수 있다.
로컬 확인: `GITHUB_TOKEN=$(gh auth token) DRY_RUN=1 BASE_SHA=<예전 커밋> python watch.py`

Gemini 3.8은 일시적 서버 오류 때 두 기존 키로 최대 3회 시도한다. 429에서는 키를 바꾸어 재시도하지 않는다. 모두 실패하면 `GROQ_API_KEY`가 있을 때 Groq(Qwen 3.8 27B)로 한 번 요약한다. Groq 입력은 작은 발췌로 제한하며 생략 여부를 알림에 표시한다.
- `GEMINI_API_KEY_BACKUP`: 두 번째 기존 Gemini 프로젝트 키(선택)
- `GROQ_API_KEY`: Groq 백업 키(선택). 뉴스봇과 같은 프로젝트라면 사용 한도를 공유한다.
