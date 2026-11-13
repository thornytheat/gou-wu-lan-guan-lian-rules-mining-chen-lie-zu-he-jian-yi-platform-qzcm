"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 品牌与业务
    brand: str = "basketrule"
    org_name: str = "拾光便利 · 品类运营中心"
    pilot_stores: int = 12
    sample_days: int = 7
    adoption_rate: float = 0.35

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "basketrule"
    db_user: str = "basketrule"
    db_password: str = "basketrule_pw_2026"
    db_schema: str = "basketrule"

    # 安全
    jwt_secret: str = "basketrule-jwt-secret-change-me-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_mining_per_minute: int = 6
    rate_limit_ingest_per_minute: int = 12
    rate_limit_default_per_minute: int = 240

    # 算法阈值（前端只展示后端回传值，不得硬编码）
    default_min_support: float = 0.01
    default_min_confidence: float = 0.05
    default_max_itemset: int = 3
    default_filter_lift: float = 1.2
    default_filter_confidence: float = 0.25
    stable_tier_lift: float = 1.15
    wilson_z: float = 1.96
    shelf_slots: int = 6

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
