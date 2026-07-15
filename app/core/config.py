"""애플리케이션 설정.

.env 파일을 실행 위치와 무관하게 로드한다 (프로젝트 루트 기준 절대경로).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ = app/core/config.py → parents[2] = 프로젝트 루트
_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _ROOT / ".env"


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "ASF-Orchestrator"

    # 관리자 웹 (HTTP Basic)
    admin_username: str = "admin"
    admin_password: str = "change-me-please"

    # 소비자 API 토큰 (빈 값이면 공개)
    consumer_api_token: str = ""

    # 캐시
    cache_db_path: str = "data/cache.db"
    cache_ttl_hours: int = 12

    # 스케줄 수집
    collect_interval_hours: int = 6
    seed_sample_on_empty: bool = True

    # 공공데이터 API 키
    mafra_api_key: str = "sample"
    # KAMIS(kamis.or.kr) 원본 Open API 인증키 — data.go.kr 래퍼가 아님
    kamis_cert_key: str = ""
    kamis_cert_id: str = "1"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cache_db_abspath(self) -> Path:
        """캐시 DB의 절대경로 (프로젝트 루트 기준)."""
        p = Path(self.cache_db_path)
        return p if p.is_absolute() else _ROOT / p


settings = Settings()
