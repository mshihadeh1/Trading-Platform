from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./data/trading.db"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # LLM
    llm_base_url: str = "http://10.50.0.30:8000/v1"
    llm_api_key: str = "dummy"
    llm_model: str = "Qwen3.6-35B-A3B-UD-Q3_K_S.gguf"

    # Frontend CORS
    frontend_url: str = "http://localhost:3000"

    # Paper trading
    initial_capital: float = 10000.0
    max_position_pct: float = 10.0
    auto_trade_min_confidence: int = 65
    max_open_trades: int = 5
    min_risk_reward_ratio: float = 1.5

    # Analysis schedule
    analysis_interval_hours: int = 4
    daily_brief_enabled: bool = True
    daily_brief_interval_hours: int = 24

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
