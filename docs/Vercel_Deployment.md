# Vercel 배포 가이드

## 1. 배포 아키텍처

ASF-Orchestrator는 Vercel에서 2개의 독립적인 프로젝트로 배포됩니다:

```
┌─────────────────────┐
│   Frontend (웹)      │
│  apps/web (React)   │
│  https://asf.xxx    │  ← Vercel (Web)
└─────────────────────┘
         ↓
    API 호출
         ↓
┌─────────────────────┐
│  Backend (API)      │
│  FastAPI + Python   │
│  https://api.xxx    │  ← Vercel (Serverless)
└─────────────────────┘
```

---

## 2. 전제 조건

- Vercel 계정 (vercel.com)
- GitHub 저장소 연결 완료
- 환경변수 설정 권한

---

## 3. 웹 프론트엔드 배포 (apps/web)

### 3.1 Vercel에서 새 프로젝트 생성

1. https://vercel.com/dashboard 접속
2. **"Add New..."** → **"Project"** 클릭
3. GitHub 저장소 선택
4. **Root Directory**: `apps/web` 설정
5. **Framework**: `Vite` (자동 감지됨)

### 3.2 빌드 설정

**Project Settings** → **Build & Development Settings**:
- **Build Command**: `npm run build` (또는 자동 감지)
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 3.3 환경변수 설정

**Project Settings** → **Environment Variables** 추가:

```
VITE_API_URL = https://asf-api-xyz.vercel.app/api/v1
```

> 주의: `VITE_` 접두사는 빌드 시점에 클라이언트에 포함되므로 민감한 정보는 절대 사용 금지

### 3.4 배포

1. GitHub에 푸시
2. Vercel이 자동으로 배포 시작
3. 배포 URL: `https://asf-xxxxxx.vercel.app`

---

## 4. 백엔드 API 배포 (services/backend)

### 4.1 Vercel에서 새 프로젝트 생성

1. https://vercel.com/dashboard 접속
2. **"Add New..."** → **"Project"** 클릭
3. GitHub 저장소 선택
4. **Root Directory**: `services/backend` 설정
5. **Framework**: `Other` (Vercel이 Python 감지)

### 4.2 빌드 설정 (자동)

Vercel이 `requirements.txt`에서 자동으로 감지:
- Runtime: Python 3.8
- Build: `npm install --save` (선택사항)

### 4.3 환경변수 설정

**Project Settings** → **Environment Variables** 추가:

```
MAFRA_API_KEY = REDACTED_MAFRA_KEY
KAMIS_API_KEY = REDACTED_KAMIS_KEY
KAMIS_API_ID = 5129
JWT_SECRET = [새로운 시크릿 생성]
APP_ENV = production
```

> ⚠️ **MAFRA API IP 화이트리스트**
>
> Vercel 서버 IP를 data.mafra.go.kr에 등록해야 합니다.
> - 배포 후 서버에서 `curl ifconfig.me`로 확인
> - MAFRA 포털에서 해당 IP를 등록

### 4.4 배포 테스트

배포 완료 후:

```bash
curl https://asf-api-xyz.vercel.app/healthz
curl https://asf-api-xyz.vercel.app/api/v1/recommendations/today
```

---

## 5. 데이터베이스 설정

### PostgreSQL 연결 (선택)

Vercel에서 데이터베이스를 제공하지 않으므로, 외부 서비스 사용:

**옵션 A: AWS RDS PostgreSQL**
```
DATABASE_URL = postgresql://user:pass@rds.amazonaws.com:5432/asf
```

**옵션 B: Neon (PostgreSQL 호스팅)**
```
DATABASE_URL = postgresql://user:pass@pg.neon.tech/asf
```

환경변수에 `DATABASE_URL` 추가하면 backend가 자동으로 사용

---

## 6. Redis 설정 (Celery용)

Vercel Serverless에서는 Redis 연결이 제한적입니다.

### 옵션 A: Redis Cloud (권장)
1. https://redis.com/try-free/ 가입
2. `CELERY_BROKER_URL` 환경변수 설정:
   ```
   CELERY_BROKER_URL = redis://user:pass@redis-cloud.com:6379/0
   ```

### 옵션 B: Celery 비활성화
- Vercel Serverless 환경에서는 scheduled tasks 불가
- AWS Lambda 또는 별도 서버에서 Celery 실행

---

## 7. 배포 체크리스트

### 프론트엔드
- [ ] Root Directory를 `apps/web`으로 설정
- [ ] Build Command: `npm run build`
- [ ] Output Directory: `dist`
- [ ] `VITE_API_URL` 환경변수 설정
- [ ] 배포 URL 테스트

### 백엔드
- [ ] Root Directory를 `services/backend`으로 설정
- [ ] Python 3.8 감지 확인
- [ ] 모든 API 키 환경변수 설정
- [ ] `/healthz` 엔드포인트 응답 확인
- [ ] `/api/v1/recommendations/today` 응답 확인
- [ ] MAFRA API IP 화이트리스트 등록

---

## 8. 배포 후 운영

### 모니터링

```bash
# 프론트엔드 빌드 로그
vercel logs https://asf-xxxxxx.vercel.app

# 백엔드 함수 로그
vercel logs https://asf-api-xxxxxx.vercel.app --follow
```

### 자동 배포

- GitHub에 푸시하면 자동으로 배포
- PR은 preview URL 생성
- main/master 병합 시 프로덕션 배포

### 환경변수 업데이트

Vercel Dashboard에서 환경변수 수정 후:
1. 프로젝트 재배포
2. 또는 Vercel CLI: `vercel env pull`

---

## 9. 문제 해결

### "Module not found" 에러
```bash
# 백엔드의 requirements.txt 확인
pip list > services/backend/requirements.txt
```

### API 호출 실패
- CORS 설정 확인 (`app/main.py`)
- 환경변수 누락 확인
- 백엔드 로그 확인

### MAFRA API 인증 에러
- Vercel 서버 IP를 data.mafra.go.kr에 등록
- 또는 sample 키로 폴백 (5건 제한)

---

## 10. CLI 설치 및 배포

### Vercel CLI 설치

```bash
npm i -g vercel
```

### 프로젝트 배포

```bash
# 프론트엔드
cd apps/web
vercel --prod

# 백엔드
cd services/backend
vercel --prod
```

### 환경변수 관리

```bash
# .env 파일을 Vercel에 업로드
vercel env pull
```

---

## 11. 다음 단계

1. **데이터베이스 연결**: PostgreSQL 구성
2. **모바일 앱**: React Native Expo로 배포
3. **CI/CD 개선**: GitHub Actions로 테스트 자동화
4. **모니터링**: Sentry 또는 LogRocket 통합
5. **캐싱**: Vercel Edge Cache 설정
