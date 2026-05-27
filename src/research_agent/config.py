from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    mistral_api_key: str = Field(default="", validation_alias="MISTRAL_API_KEY")
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    github_token: str = Field(default="", validation_alias="GITHUB_TOKEN")

    log_level: str = Field(default="INFO", validation_alias="RESEARCH_AGENT_LOG_LEVEL")
    reports_dir: Path = Field(default=Path("./reports"), validation_alias="RESEARCH_AGENT_REPORTS_DIR")
    chroma_path: Path = Field(default=Path("./.chroma_cache"), validation_alias="RESEARCH_AGENT_CHROMA_PATH")
    http_timeout: float = Field(default=20.0, validation_alias="RESEARCH_AGENT_HTTP_TIMEOUT")
    max_embed_calls: int = Field(default=100, validation_alias="RESEARCH_AGENT_MAX_EMBED_CALLS")

    mistral_chat_model: str = Field(
        default="mistral-large-latest", validation_alias="RESEARCH_AGENT_MISTRAL_CHAT_MODEL"
    )
    mistral_embed_model: str = Field(
        default="mistral-embed", validation_alias="RESEARCH_AGENT_MISTRAL_EMBED_MODEL"
    )

    embed_dim: int = 1024


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
