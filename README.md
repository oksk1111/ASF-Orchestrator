# ASF-Orchestrator Platform

ASF-Orchestrator 문서(Proposal/SRS/LLD)를 기준으로 구현한 모듈형 서비스 플랫폼입니다.

구성
- services/backend: FastAPI 기반 API, 추천/예측/동적가격/물류 최적화 모듈
- apps/web: React + Vite 기반 B2B/B2C 통합 웹앱
- apps/mobile: React Native(Expo) 기반 모바일 앱 프로토타입
- shared/design-tokens: design-system-spec.json 기반 토큰
- proto/logistics/v1: 물류 gRPC 계약(proto)
- infra: 로컬 인프라 도커 컴포즈

## 1) Backend 실행

필수: Python 가상환경

PowerShell 예시
1. c:/Users/oksk1/workspace/ASF-Orchestrator/.venv/Scripts/python.exe -m pip install -r services/backend/requirements.txt
2. c:/Users/oksk1/workspace/ASF-Orchestrator/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir services/backend --reload --port 8000

테스트
- c:/Users/oksk1/workspace/ASF-Orchestrator/.venv/Scripts/python.exe -m pytest services/backend/tests -q

## 2) Web 실행

1. npm install
2. npm run web:dev

환경변수(선택)
- apps/web/.env 파일 생성 후 VITE_API_BASE_URL=http://localhost:8000

## 3) Mobile 실행

1. npm install
2. npm run mobile:start

## 4) 핵심 API

- GET /api/v1/recommendation/basket
- POST /api/v1/logistics/route
- POST /api/v1/checkout
- GET /api/v1/forecast/pricing
- POST /api/v1/auth/token
- GET /metrics

## 5) 디자인 적용 원칙

웹(concept01)
- announcementGreen(#1E3A2B), forestGreen(#2C4F3E), limeAccent(#C5E042)
- 섹션/카드 그림자와 라운드 규칙 준수

모바일(concept02)
- monochrome + urgencyGold(#C08A2A) 단일 강조
- 바텀 시트, pill CTA, 원형 사이즈 셀렉터 규칙 준수
