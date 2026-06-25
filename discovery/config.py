from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mock_mode: bool = True
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/mvp/callback"
    api_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:4321"
    data_dir: str = "data"
    corpus_path: str = "data/corpus.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
