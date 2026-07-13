# FreshAlert Platform

FreshAlert는 실시간 신선식품 가격 모니터링 및 추천 서비스 플랫폼입니다. 사용자 건강 목표와 시장 수급 데이터를 결합하여 최적의 식품 추천을 제공합니다.

구성
- services/backend: FastAPI 기반 REST API, Fresh-Alert 추천/예측 엔진
- apps/web: React + Vite 기반 웹 대시보드
- apps/mobile: React Native(Expo) 기반 모바일 앱
- shared/design-tokens: design-system-spec.json 기반 토큰
- infra: 로컬 개발환경 Docker Compose

## 1) Backend 실행

필수: Python 가상환경 및 8100 포트

Linux/macOS 예시
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/backend/requirements.txt
python -m uvicorn app.main:app --app-dir services/backend --reload --port 8100
```

WindowsPowerShell 예시
```ps1
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r services/backend/requirements.txt
python -m uvicorn app.main:app --app-dir services/backend --reload --port 8100
```

테스트
```bash
python -m pytest services/backend/tests -v
```

## 2) Web 실행

```bash
npm install
npm run web:dev
```

환경변수 (`.env` 파일 생성)
```
VITE_API_URL=http://localhost:8100/api/v1
VITE_API_BASE_URL=http://localhost:8100
```

접속: http://localhost:5173 또는 http://localhost:5174

## 3) Mobile 실행

```bash
npm install
npm run mobile:start
```

## 4) FreshAlert 핵심 API

### 인증
- POST `/api/v1/auth/token` - 토큰 발급

### 추천 및 알림
- GET `/api/v1/fresh-alert/recommendations/today` - 오늘의 추천
- GET `/api/v1/fresh-alert/keywords?user_id=<id>` - 키워드 구독 목록
- GET `/api/v1/fresh-alert/notifications?user_id=<id>&limit=20` - 가격 변동 알림
- GET `/api/v1/fresh-alert/seasons/current` - 이달의 제철 상품

### 기타 서비스
- GET `/api/v1/recommendation/basket` - AI 장바구니
- GET `/api/v1/forecast/pricing` - 가격 예측
- POST `/api/v1/logistics/route` - 배송 경로 최적화

## 5) 디자인 적용 원칙

웹 (Concept: FreshAlert)
- announcementGreen(#1E3A2B), forestGreen(#2C4F3E), limeAccent(#C5E042)
- 신선식품 테마: 자연/건강/신뢰 이미지

모바일
- monochrome + urgencyGold(#C08A2A)
- 빠른 알림과 직관적 네비게이션
