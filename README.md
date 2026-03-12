# Global Issue Map

FastAPI, Jinja2, MongoDB Atlas, NewsAPI, OpenAI, Naver Papago 기반의 세계 이슈 지도 서비스 골격입니다.

## 실행 준비

1. `python -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `.env.example`를 참고해 `.env` 생성
5. `uvicorn app.main:app --reload`

## 현재 포함 내용

- 페이지 라우트: 홈, 카테고리 4종, 나만의 기사
- API 라우트: 뉴스 조회, 검색, 상세, AI 분석, 저장 기사 CRUD
- 익명 세션 쿠키 `gid_session`
- MongoDB 인덱스 초기화
- APScheduler 기반 뉴스 수집, Papago 번역, AI 분석, 정리 작업
- Leaflet 기반 지도 UI 뼈대
- Papago 기반 기사 제목, 요약, 본문, 카테고리 한글화

## 환경 변수

- `NEWSAPI_API_KEY`: 실뉴스 수집용
- `OPENAI_API_KEY`: AI 분석용
- `PAPAGO_API_KEY_ID`, `PAPAGO_API_KEY`: Papago 번역용
- `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET`: 기존 별칭으로도 사용 가능
- `MONGODB_URI`: MongoDB Atlas 또는 외부 MongoDB 연결 문자열
- `MONGODB_DB_NAME`: 기본 DB 이름, 기본값 `global_issue_map`

## Render 배포

현재 구조는 `APScheduler`와 startup 작업이 돌아가는 장기 실행 FastAPI 앱이라서, 서버리스보다는 Render 같은 웹 서비스 배포에 잘 맞습니다.

프로젝트에는 아래 배포 파일이 포함되어 있습니다.

- `render.yaml`: Render Blueprint 설정
- `.python-version`: Python 버전 고정
- `/healthz`: 헬스체크 엔드포인트

배포 순서:

1. GitHub 저장소를 Render에 연결합니다.
2. Render에서 `New +` -> `Blueprint` 또는 `Web Service`를 선택합니다.
3. 루트는 프로젝트 루트 그대로 사용합니다.
4. 환경 변수에 아래 값을 넣습니다.
   - `MONGODB_URI`
   - `NEWSAPI_API_KEY`
   - `PAPAGO_API_KEY_ID`
   - `PAPAGO_API_KEY`
   - `OPENAI_API_KEY`
5. 배포 후 `/healthz`가 `{"status":"ok"}`를 반환하면 정상입니다.

기본 시작 명령은 아래와 같습니다.

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
```

## 주의 사항

- 실제 뉴스 수집은 `NEWSAPI_API_KEY`가 있어야 동작합니다.
- 실제 AI 분석은 `OPENAI_API_KEY`가 있어야 동작합니다.
- Papago 키가 없으면 번역 필드는 비어 있고 원문이 그대로 표시됩니다.
- 배포 환경에서는 로컬 MongoDB 대신 외부 MongoDB Atlas 연결이 필요합니다.
- 현재 구조는 내부 스케줄러를 쓰므로 Vercel 같은 서버리스 환경보다는 Render, Railway, Fly.io 같은 장기 실행 환경이 더 적합합니다.
