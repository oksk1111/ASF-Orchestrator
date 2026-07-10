# AGENTS.md — ASF-Orchestrator 코딩 규칙

> 이 문서는 AI 에이전트 및 개발자가 본 프로젝트에서 코드를 작성할 때 따라야 할 규칙을 정의합니다.

---

## 1. 프로젝트 구조

```
ASF-Orchestrator/
├── apps/
│   ├── web/                  # React + Vite (TypeScript)
│   └── mobile/               # React Native + Expo (TypeScript)
├── services/
│   └── backend/              # FastAPI (Python)
│       ├── app/
│       │   ├── api/routes/   # API 라우트 (도메인별 파일 분리)
│       │   ├── core/         # 설정, 보안 등 공통 모듈
│       │   ├── domain/       # Pydantic 도메인 모델
│       │   ├── repositories/ # 데이터 접근 계층
│       │   └── services/     # 비즈니스 로직 (도메인별 패키지)
│       ├── migrations/       # SQL 마이그레이션 파일
│       └── tests/            # pytest 테스트
├── infra/                    # Docker, IaC
├── docs/                     # 기획서, 설계 문서
├── proto/                    # gRPC proto 정의
└── shared/                   # 공유 디자인 토큰
```

---

## 2. Python 백엔드 규칙 (`services/backend/`)

### 2.1 필수 헤더

모든 `.py` 파일의 첫 줄에 반드시 포함:

```python
from __future__ import annotations
```

> Python 3.8 호환성을 위해 필수. `list[str]`, `dict[str, Any]`, `str | None` 문법 사용을 위함.

### 2.2 모듈 독스트링

모든 모듈 파일의 상단에 한글 또는 영문 독스트링을 작성한다:

```python
"""모듈의 목적을 한 줄로 설명.

필요시 추가 설명을 이어서 작성한다.
"""
```

### 2.3 임포트 순서

```python
from __future__ import annotations          # 1. future

import logging                               # 2. 표준 라이브러리
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import httpx                                 # 3. 서드파티
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings         # 4. 프로젝트 내부
from app.domain.fresh_alert_models import Item
```

### 2.4 타입 힌트

- **모든** 함수/메서드에 인자 타입과 반환 타입을 명시한다.
- Optional은 `str | None` 문법을 사용한다 (`Optional[str]` 아님).
- 컬렉션은 `list[str]`, `dict[str, Any]` 문법을 사용한다 (`List`, `Dict` 아님).

```python
def get_item(self, item_id: str) -> Item | None:
    return self.items.get(item_id)
```

### 2.5 Pydantic 모델 (도메인)

- `app/domain/` 디렉토리에 도메인별 파일로 분리한다.
- `BaseModel`을 상속하며, 제약조건은 `Field`로 표현한다.
- Enum 대신 `Literal` 타입을 사용한다.
- 응답 봉투 패턴: `Envelope(status="success", data=...)` 형태.

```python
class DailyAnalysis(BaseModel):
    item_id: str
    analysis_date: str
    recommend_score: float = Field(ge=0.0, le=1.0)

class FreshAlertEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: Any
```

### 2.6 서비스 레이어

- 도메인별로 `app/services/{domain}/` 패키지를 생성한다.
- 각 패키지에 `__init__.py`로 public API를 명시한다.
- 비즈니스 로직은 **순수 함수**로 작성하고, I/O는 별도 모듈에 분리한다.
- 클래스보다 함수를 선호하되, 상태가 필요한 경우(예: HTTP 클라이언트) 클래스 사용.

```
services/fresh_alert/
├── __init__.py          # public exports
├── analyzer.py          # 순수 함수 (계산 로직)
├── collector.py         # I/O (외부 API 호출)
├── repository.py        # 데이터 저장/조회
├── alert_service.py     # 알림 생성 로직
├── scheduler.py         # 배치 스케줄링
└── season_data.py       # 상수/참조 데이터
```

### 2.7 API 라우트

- `app/api/routes/{domain}.py` 파일로 도메인별 분리한다.
- 라우터 prefix와 tags를 명시한다.
- 섹션 구분에 주석 헤더를 사용한다.

```python
router = APIRouter(prefix="/fresh-alert", tags=["FreshAlert"])

# ─── 추천 ────────────────────────────────────────────────────────

@router.get("/recommendations/today")
def get_today_recommendations() -> FreshAlertEnvelope:
    ...
```

- 새 라우트 파일 추가 시 `app/api/routes/__init__.py`에 등록한다.

### 2.8 설정 관리

- `app/core/config.py`의 `Settings` 클래스에 환경변수를 추가한다.
- `.env.example`에 새 환경변수를 반드시 기록한다.
- 비밀값의 기본값은 `"sample"` 또는 빈 문자열로 둔다.

```python
class Settings(BaseSettings):
    mafra_api_key: str = "sample"
    fresh_alert_recommend_top_n: int = 5
```

### 2.9 에러 처리

- 외부 API 호출 시 빈 결과 반환 + 로깅 (예외를 삼키지 않는다).
- 사용자 입력 에러: `HTTPException(status_code=4xx, detail="한글 메시지")`.
- 내부 오류: 로깅 후 500 응답 (FastAPI 기본 동작).

```python
except httpx.HTTPStatusError as exc:
    logger.error("HTTP %d from MAFRA API: %s", exc.response.status_code, exc.response.text[:200])
    return []
```

### 2.10 리포지토리 패턴

- MVP 단계에서는 `InMemory` 리포지토리를 사용한다.
- 모듈 레벨 싱글턴으로 인스턴스를 생성한다: `fresh_alert_repo = FreshAlertRepository()`
- 읽기 메서드는 `deepcopy`로 반환하여 외부 mutation을 방지한다.
- 목업 데이터는 `random.Random(42)` (시드 고정)로 재현 가능하게 생성한다.

### 2.11 상수 & 참조 데이터

- 도메인 상수는 별도 파일 (예: `season_data.py`)에 모은다.
- 딕셔너리 상수는 `UPPER_SNAKE_CASE`를 사용한다.
- 섹션 구분에 주석 블록을 사용한다:

```python
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
```

### 2.12 테스트

- `tests/test_{domain}.py` 형식으로 파일 분리.
- `pytest` + `fastapi.testclient.TestClient` 사용.
- 테스트 클래스는 기능 단위로 그룹핑: `class TestMovingAverage:`, `class TestFreshAlertAPI:`.
- 단위 테스트 → 통합 테스트 순서로 구성한다.
- 모든 API 엔드포인트는 최소 1개의 통합 테스트를 갖는다.

```python
class TestFreshAlertAPI:
    def test_get_recommendations(self):
        resp = client.get("/api/v1/fresh-alert/recommendations/today")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
```

---

## 3. TypeScript 프론트엔드 규칙 (`apps/web/`, `apps/mobile/`)

### 3.1 공통

- TypeScript strict 모드 사용.
- 절대 경로 임포트 (`@/` 또는 `src/` 접두사).
- 컴포넌트: `PascalCase.tsx`, 유틸: `camelCase.ts`.
- 인터페이스 접두사 `I` 사용하지 않는다 (예: `User`, not `IUser`).

### 3.2 Web (`apps/web/`)

- React 18 + Vite + TypeScript.
- 상태 관리: React Context 또는 Zustand (Redux 아님).
- 스타일: CSS Modules 또는 Tailwind CSS.
- API 클라이언트: `src/api/client.ts`에 집중.

### 3.3 Mobile (`apps/mobile/`)

- React Native 0.74 + Expo SDK 51.
- 디자인 토큰: `src/theme/tokens.ts` 참조.
- 네비게이션: Expo Router.

---

## 4. 데이터베이스 규칙

### 4.1 마이그레이션

- `services/backend/migrations/` 디렉토리에 순번 파일 생성.
- 파일명: `{NNN}_{description}.sql` (예: `001_fresh_alert_schema.sql`).
- 각 마이그레이션은 `BEGIN;` ... `COMMIT;`으로 감싼다.
- `CREATE TABLE IF NOT EXISTS`로 멱등성을 보장한다.

### 4.2 테이블 네이밍

- 도메인 접두사 사용: `fa_` (FreshAlert), `asf_` (공통).
- snake_case 사용.
- 인덱스: `idx_{table}_{columns}` 형식.

```sql
CREATE TABLE fa_items (...);
CREATE INDEX idx_fa_items_category ON fa_items(large_code, mid_code);
```

---

## 5. Git 규칙

### 5.1 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 형식:

```
<type>: <subject>

<body (optional)>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**타입:**
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드/설정 변경

### 5.2 브랜치

- `master`: 메인 브랜치 (직접 푸시 가능, 단 테스트 통과 필수).
- `feat/{description}`: 기능 브랜치 (대규모 작업 시).

### 5.3 커밋 전 체크리스트

1. `cd services/backend && python -m pytest tests/ -v` — 전체 테스트 통과
2. 새 환경변수 → `.env.example` 업데이트
3. 새 라우트 → `routes/__init__.py` 등록
4. 새 패키지 → `requirements.txt` 추가

---

## 6. 문서화 규칙

- 기획서, 설계서: `docs/` 디렉토리에 Markdown으로 작성.
- API 문서: FastAPI 자동생성 (`/docs` 엔드포인트) + 독스트링.
- 주석 언어: 한글 (코드 내 독스트링은 한글 또는 영문 가능).
- 인라인 주석은 최소화하되, "왜"를 설명할 때 사용한다.

---

## 7. 환경 및 의존성

| 레이어 | 기술 | 버전 |
|--------|------|------|
| Python | CPython | 3.8+ (3.10+ 권장) |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic | 2.10+ |
| HTTP Client | httpx | 0.27+ |
| Test | pytest | 8.3+ |
| Web | React + Vite | 18 + 5 |
| Mobile | React Native + Expo | 0.74 + SDK 51 |
| DB | PostgreSQL | 16 |
| Cache | Redis | 7 |

### 의존성 추가 시

- Python: `services/backend/requirements.txt`에 **고정 버전**으로 추가.
- Node: 해당 `apps/` 하위의 `package.json`에 추가.

---

## 8. 보안 규칙

- API 키, 시크릿은 절대 코드에 하드코딩하지 않는다.
- `.env` 파일은 `.gitignore`에 포함 (커밋하지 않음).
- JWT 토큰 기반 인증 (`Bearer` 헤더).
- Rate limiting: IP당 분당 120회 기본 (미들웨어).

---

## 9. 코드 스타일 요약

| 항목 | Python | TypeScript |
|------|--------|------------|
| 들여쓰기 | 4 spaces | 2 spaces |
| 줄 길이 | 100자 (soft limit) | 100자 |
| 따옴표 | 큰따옴표 (`"`) | 큰따옴표 (`"`) |
| Trailing comma | 사용 | 사용 |
| Semicolons | N/A | 없음 |
| Naming (변수/함수) | snake_case | camelCase |
| Naming (클래스) | PascalCase | PascalCase |
| Naming (상수) | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE |

---

## 10. AI 에이전트 지침

AI 에이전트가 코드를 생성할 때 추가로 따를 규칙:

1. **기존 패턴을 따른다** — 새 파일 작성 전 같은 레이어의 기존 파일을 참조.
2. **한글 주석 허용** — 독스트링과 주석은 한글 사용 가능.
3. **테스트 필수** — 새 기능은 반드시 테스트와 함께 작성.
4. **작은 단위 커밋** — 기능 단위로 분리하여 커밋.
5. **TODO 주석** — 미완성 기능은 `# TODO:` 주석으로 명시.
6. **에러 시 재시도 금지** — 같은 실패 코드를 반복하지 않고 원인을 분석.
7. **목업 우선** — 외부 연동은 먼저 목업으로 구현 후, 실제 연동을 분리.
