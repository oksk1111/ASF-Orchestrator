# FreshAlert 배포 및 운영 가이드

## 1. API 키 설정

### MAFRA (농림축산식품부 도매시장 데이터)

- **발급처**: https://data.mafra.go.kr
- **인증키**: `REDACTED_MAFRA_KEY`
- **허용 IP**: `10.157.78.49` (공유기 IP)
- **중요**: MAFRA API는 등록된 IP에서만 호출 가능. 서버 IP가 변경되면 data.mafra.go.kr에서 IP 재등록 필요.

```bash
# .env 파일에 설정
MAFRA_API_KEY=REDACTED_MAFRA_KEY
```

> ⚠️ **IP 화이트리스트 주의사항**
> - 클라우드 배포 시 서버의 outbound IP를 확인하여 MAFRA 포털에 재등록해야 합니다.
> - AWS EC2: `curl ifconfig.me`로 public IP 확인
> - Docker: host의 public IP가 사용됨
> - 로컬 개발 시 공유기 외부 IP와 등록 IP가 일치해야 합니다.

### KAMIS (농산물유통정보)

- **발급처**: data.go.kr (공공데이터포털)
- **End Point**: `https://www.kamis.or.kr/service/price/xml.do` (실제 작동 URL)
- **Cert ID**: `5129`
- **IP 제한**: 없음 (어디서든 호출 가능)

```bash
KAMIS_API_KEY=REDACTED_KAMIS_KEY
KAMIS_API_ID=5129
```

> 참고: data.go.kr에서 발급된 End Point(`https://apis.data.go.kr/B552845/perDay`)는 500 에러를 반환합니다.
> 실제 작동하는 URL은 `https://www.kamis.or.kr/service/price/xml.do`입니다.

---

## 2. 로컬 개발 환경 설정

### 사전 요구사항

- Python 3.8+
- Redis 7 (Celery 브로커용)
- PostgreSQL 16 (추후 마이그레이션 시)

### 빠른 시작

```bash
# 1. 백엔드 의존성 설치
cd services/backend
pip install -r requirements.txt

# 2. .env 파일 생성
cp .env.example .env
# → API 키 입력

# 3. 서버 실행
uvicorn app.main:app --reload --port 8000

# 4. 파이프라인 수동 실행 (데이터 수집)
python scripts/run_pipeline.py --date 20260710

# 5. API 확인
open http://localhost:8000/docs
```

### Celery 스케줄러 실행

```bash
# Redis 필요
redis-server &

# Celery 실행
./scripts/start_celery.sh

# 또는 개별 실행
celery -A app.services.fresh_alert.celery_app worker --loglevel=info
celery -A app.services.fresh_alert.celery_app beat --loglevel=info
```

---

## 3. Docker 배포

```bash
cd infra

# 환경변수 설정 (.env 파일 또는 export)
export MAFRA_API_KEY=REDACTED_MAFRA_KEY
export KAMIS_API_KEY="REDACTED_KAMIS_KEY"
export KAMIS_API_ID=5129

# 전체 서비스 실행
docker compose up -d

# 서비스 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f celery-worker
docker compose logs -f celery-beat
```

### 서비스 구성

| 서비스 | 포트 | 역할 |
|--------|------|------|
| backend | 8000 | FastAPI 서버 |
| celery-worker | - | 배치 작업 실행 |
| celery-beat | - | 스케줄 관리 |
| postgres | 5432 | 데이터베이스 |
| redis | 6379 | Celery 브로커 / 캐시 |
| rabbitmq | 5672/15672 | 메시지 큐 (추후) |

---

## 4. 스케줄 일정 (KST)

| 시간 | 작업 | 설명 |
|------|------|------|
| 06:00 | collect_kamis_daily | KAMIS 소매가격 수집 |
| 06:15 | collect_mafra_daily | MAFRA 도매가격 수집 |
| 06:30 | run_daily_analysis | 일별 분석 (이동평균, 이상치, 점수) |
| 07:00 | generate_recommendations | 오늘의 추천 TOP 5 생성 |
| 07:00 | check_keyword_alerts | 키워드 알림 확인 (아침) |
| 12:00 | check_keyword_alerts | 키워드 알림 확인 (점심) |
| 18:00 | check_keyword_alerts | 키워드 알림 확인 (저녁) |

---

## 5. FCM 푸시 알림 설정

### Firebase 프로젝트 설정

1. Firebase Console → 프로젝트 생성
2. Cloud Messaging → 서비스 계정 키(JSON) 다운로드
3. 다운로드한 JSON을 서버에 배치

```bash
# .env에 경로 설정
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-service-account.json
```

### 개발 모드

Firebase 설정 없이도 서버는 정상 작동합니다.
알림은 로그에만 출력되고 실제 푸시는 전송되지 않습니다.

---

## 6. DB 마이그레이션

```bash
# PostgreSQL에 스키마 적용
psql -h localhost -U asf -d asf -f migrations/001_fresh_alert_schema.sql
```

---

## 7. 모니터링

### 헬스 체크

```bash
curl http://localhost:8000/api/v1/healthz
curl http://localhost:8000/metrics
```

### 파이프라인 수동 트리거

```bash
# API를 통한 수동 실행
curl -X POST "http://localhost:8000/api/v1/fresh-alert/pipeline/run?date=20260710"

# CLI를 통한 수동 실행
python scripts/run_pipeline.py --step full --date 20260710
```

---

## 8. 트러블슈팅

### MAFRA API "인증키가 유효하지 않습니다"

- **원인**: 요청 서버 IP가 등록된 IP(`10.157.78.49`)와 다름
- **해결**: data.mafra.go.kr → 마이페이지 → API 관리 → 허용 IP 수정
- **확인**: `curl ifconfig.me`로 현재 서버의 외부 IP 확인

### KAMIS API 500 에러

- **data.go.kr URL**: `https://apis.data.go.kr/B552845/perDay` → 500 에러 (사용하지 않음)
- **실제 작동 URL**: `https://www.kamis.or.kr/service/price/xml.do` → 정상
- 코드에서는 올바른 URL을 사용하고 있으므로 문제 없음

### sample 키로 MAFRA 5건 제한

- `sample` 키는 한 번에 최대 5건만 조회 가능
- 실제 키로 전환 시 최대 1,000건 조회 가능
- collector가 자동으로 페이징 처리함
