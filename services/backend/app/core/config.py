from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ASF-Orchestrator Backend"
    app_env: str = "dev"
    jwt_secret: str = "asf-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 24 * 60
    rate_limit_per_minute: int = 120

    # Multi-objective coefficients
    alpha: float = 0.40
    beta: float = 0.50
    gamma: float = 0.10

    # Dynamic pricing constraints
    min_discount_rate: float = 0.05
    max_discount_rate: float = 0.30

    # FreshAlert settings
    mafra_api_key: str = "sample"
    kamis_api_key: str = ""
    kamis_api_id: str = ""
    fresh_alert_notify_time: str = "07:00"
    fresh_alert_recommend_top_n: int = 5
    fresh_alert_default_threshold: float = -15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
