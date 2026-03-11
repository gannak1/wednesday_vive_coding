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

## 주의 사항

- 실제 뉴스 수집은 `NEWSAPI_API_KEY`가 있어야 동작합니다.
- 실제 AI 분석은 `OPENAI_API_KEY`가 있어야 동작합니다.
- Papago 키가 없으면 번역 필드는 비어 있고 원문이 그대로 표시됩니다.
- 데이터베이스 연결이 없으면 페이지는 빈 상태 또는 오류 배너로 보일 수 있습니다.
