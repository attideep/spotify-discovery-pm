import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SESSION_SECRET = "change-me-in-production"
MIN_SESSION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mock_mode: bool = False
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    database_url: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "https://spotify-discovery-pm.vercel.app/mvp/callback"
    session_secret: str = DEFAULT_SESSION_SECRET
    google_client_id: str = ""
    google_client_secret: str = ""
    api_base_url: str = "https://spotify-discovery-pm.vercel.app"
    web_base_url: str = "https://spotify-discovery-pm.vercel.app"
    data_dir: str = "data"
    corpus_path: str = "data/corpus.json"
    allow_demo_mode: bool = True
    rate_limit_per_minute: int = 30
    # Set true only when OpenAI billing is active — avoids 10s timeouts on quota errors
    openai_bridge_planner_enabled: bool = False

    @property
    def effective_openai_key(self) -> str:
        return self.openai_api_key.strip()

    @property
    def openai_api_key_valid(self) -> bool:
        key = self.effective_openai_key
        return key.startswith("sk-") and len(key) >= 20

    @property
    def effective_gemini_key(self) -> str:
        return (self.gemini_api_key or self.google_api_key).strip()

    @property
    def gemini_api_key_valid(self) -> bool:
        """Google AI Studio keys start with AIza — used only for optional embeddings."""
        key = self.effective_gemini_key
        return key.startswith("AIza") and len(key) >= 30

    @property
    def bridge_planner_configured(self) -> bool:
        return self.openai_api_key_valid and self.openai_bridge_planner_enabled

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def persistence_enabled(self) -> bool:
        return bool(self.database_url.strip())

    @property
    def deployed_environment(self) -> bool:
        return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

    def validate_session_secret(self) -> None:
        if not self.deployed_environment:
            return
        secret = self.session_secret.strip()
        if secret == DEFAULT_SESSION_SECRET or len(secret) < MIN_SESSION_SECRET_LENGTH:
            raise RuntimeError(
                "SESSION_SECRET must be set to a strong random value in deployed environments."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
