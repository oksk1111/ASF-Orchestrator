# ASF-Orchestrator

**농식품 공공데이터 오케스트레이션 중간 서버**

`ASF-Orchestrator`는 소비자 앱(`fresh_alert`)과 공공데이터 포털(MAFRA, KAMIS 등) 사이에 위치하는 **데이터 중간 서버**입니다. 공공 API 키를 안전하게 보관하고, 원천 데이터를 수집·정규화·캐싱하여 소비자 앱에 일관된 API로 제공합니다.

```
┌─────────────┐        ┌──────────────────────┐        ┌────────────────────┐
│ fresh_alert │  HTTP  │   ASF-Orchestrator   │  HTTP  │  공공데이터 포털    │
│ (web/mobile)│ ─────▶ │  (this middle server)│ ─────▶ │  MAFRA / KAMIS 등  │
└─────────────┘        └──────────────────────┘        └────────────────────┘
                              │  SQLite 캐시
                              │  Admin 웹 UI
                              ▼
                        스케줄 수집 + 로그
```

## 왜 중간 서버인가

- **API 키 은닉**: 공공 API 키가 소비자(웹/모바일)에 노출되지 않음.
- **캐싱**: 포털 호출을 줄이고(무료 트래픽 한도 절약) 응답을 빠르게.
- **정규화**: 서로 다른 포털의 스키마를 내부 표준 스키마로 통일.
- **운영성**: Admin 웹에서 수집 상태·로그·수동 수집을 관리.

## 구성

| 레이어 | 설명 |
|--------|------|
| `app/collectors` | MAFRA, KAMIS(data.go.kr) 수집기 |
| `app/cache` | SQLite 캐시 저장소 (가격 레코드 + 수집 로그) |
| `app/services` | 수집 오케스트레이션 |
| `app/api` | 소비자용/관리용 REST API |
| `app/admin` | 관리자 웹 UI (Jinja2 + HTTP Basic) |

## 빠른 시작

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # 값 채우기
uvicorn app.main:app --reload --port 8100
```

- 소비자 API: <http://localhost:8100/api/v1/...>
- 관리자 웹: <http://localhost:8100/admin> (기본 계정: `.env`의 `ADMIN_USERNAME`/`ADMIN_PASSWORD`)
- API 문서: <http://localhost:8100/docs>

## 배포

Oracle Cloud Always Free VM 배포 가이드는 [deploy/oracle-cloud.md](deploy/oracle-cloud.md) 참고.

## 소비자 앱 연동

`fresh_alert` 앱은 공공 포털 대신 이 서버를 호출합니다.
`fresh_alert` 백엔드의 `ASF_ORCHESTRATOR_BASE_URL`을 이 서버 주소로 설정하세요.
