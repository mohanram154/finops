import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_MODE: str = "real"  # 'real', 'simulation', or 'real'
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    DATABASE_TYPE: str = "sqlite"  # 'mongodb', 'postgresql', 'sqlite'
    DATABASE_URL: str = "sqlite:///./nexus_finops.db"
    CACHE_TYPE: str = "inmemory"  # 'redis', 'inmemory'
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_simulation_mode(self) -> bool:
        return self.APP_MODE.lower() in ("real", "simulation")

@lru_cache()
def get_settings() -> Settings:
    return Settings()

