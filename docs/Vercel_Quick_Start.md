# Vercel 배포 빠른 시작

## 1분 안에 시작하기

### 전제조건
- Vercel 계정 생성 (vercel.com)
- GitHub 저장소 연결 완료

---

## Step 1: 프론트엔드 배포 (apps/web)

### Vercel Dashboard에서
1. **Add New Project** 클릭
2. GitHub에서 `ASF-Orchestrator` 저장소 선택
3. **Root Directory**: `apps/web` 입력
4. **Framework Preset**: `Vite` (자동 감지)
5. **Environment Variables** 탭:
   ```
   Key: VITE_API_URL
   Value: https://asf-api-xyz.vercel.app/api/v1
   ```
   (백엔드 도메인으로 나중에 업데이트)
6. **Deploy** 클릭

### 배포 완료
```
✓ Your frontend is live at: https://asf-xxx.vercel.app
```

---

## Step 2: 백엔드 배포 (services/backend)

### Vercel Dashboard에서
1. **Add New Project** 클릭
2. GitHub에서 동일 저장소 선택
3. **Root Directory**: `services/backend` 입력
4. **Framework Preset**: `Other` (Python 자동 감지)
5. **Environment Variables** 탭에서 한 번에 추가:

```
MAFRA_API_KEY=<data.mafra.go.kr에서 발급한 키>
KAMIS_API_KEY=<data.go.kr에서 발급한 일반 인증키(Decoding)>
KAMIS_API_ID=5129
JWT_SECRET=<32자 이상 강력한 랜덤 문자열>
APP_ENV=production
```

6. **Deploy** 클릭

### 배포 완료
```
✓ Your API is live at: https://asf-api-xxx.vercel.app
```

---

## Step 3: 프론트엔드 환경변수 업데이트

### 프론트엔드 프로젝트의 Settings에서
1. **Environment Variables** 클릭
2. `VITE_API_URL` 값을 백엔드 도메인으로 변경:
   ```
   https://asf-api-xxx.vercel.app/api/v1
   ```
3. 프로젝트 **Redeploy** (또는 GitHub에 커밋하면 자동 배포)

---

## 확인

### 프론트엔드 테스트
```bash
curl https://asf-xxx.vercel.app
# ✓ HTML 페이지 반환
```

### 백엔드 테스트
```bash
curl https://asf-api-xxx.vercel.app/api/v1/healthz
# ✓ {"status": "ok"} 반환
```

### 통합 테스트
프론트엔드에서 개발자 도구(F12) 열어서:
- Network 탭에서 API 호출 확인
- CORS 에러 없는지 확인
- 추천 데이터 로드 확인

---

## 문제 해결

### "Environment Variable ... references Secret ... which does not exist"
❌ **원인**: `@secret_name` 형식 사용
✅ **해결**: Environment Variables 탭에서 직접 값 입력 (Secrets 아님)

### "MAFRA API 인증 에러"
❌ **원인**: Vercel 서버 IP가 등록되지 않음
✅ **해결**: 
1. 배포 로그에서 `curl ifconfig.me` 명령 실행해 IP 확인
2. data.mafra.go.kr 포털에서 해당 IP 등록

### "CORS 에러"
❌ **원인**: 백엔드의 allowed_origins에 프론트엔드 도메인 미등록
✅ **해결**: 자동으로 `https://*.vercel.app` 허용 설정됨

---

## 자동 배포

GitHub에 푸시하면 Vercel이 자동 배포:

```bash
git add .
git commit -m "fix: update API URL"
git push origin master
```

배포 상태는 Vercel Dashboard에서 확인 가능.

---

## 주요 URL

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | `https://asf-xxx.vercel.app` |
| 백엔드 API | `https://asf-api-xxx.vercel.app` |
| API 문서 | `https://asf-api-xxx.vercel.app/docs` |
| 메트릭 | `https://asf-api-xxx.vercel.app/metrics` |

---

## 다음 단계

- [ ] 데이터베이스 연결 (PostgreSQL)
- [ ] Redis 설정 (Celery scheduler)
- [ ] 모니터링 (Sentry)
- [ ] 커스텀 도메인 설정
