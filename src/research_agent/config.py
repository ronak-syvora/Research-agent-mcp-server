from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so the path is correct regardless of CWD
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

# Anchor writable data to the user home dir so paths don't resolve to a
# read-only CWD (e.g. "/") when launched by Claude Desktop or another host.
_DATA_DIR = Path.home() / ".research-agent"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    mistral_api_key: str = Field(default="", validation_alias="MISTRAL_API_KEY")
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    github_token: str = Field(default="", validation_alias="GITHUB_TOKEN")

    log_level: str = Field(default="INFO", validation_alias="RESEARCH_AGENT_LOG_LEVEL")
    reports_dir: Path = Field(default=_DATA_DIR / "reports", validation_alias="RESEARCH_AGENT_REPORTS_DIR")
    chroma_path: Path = Field(default=_DATA_DIR / "chroma_cache", validation_alias="RESEARCH_AGENT_CHROMA_PATH")
    http_timeout: float = Field(default=20.0, validation_alias="RESEARCH_AGENT_HTTP_TIMEOUT")
    max_embed_calls: int = Field(default=100, validation_alias="RESEARCH_AGENT_MAX_EMBED_CALLS")

    mistral_chat_model: str = Field(
        default="mistral-large-latest", validation_alias="RESEARCH_AGENT_MISTRAL_CHAT_MODEL"
    )
    mistral_embed_model: str = Field(
        default="mistral-embed", validation_alias="RESEARCH_AGENT_MISTRAL_EMBED_MODEL"
    )

    embed_dim: int = 1024

    @field_validator("reports_dir", "chroma_path")
    @classmethod
    def _expand_path(cls, v: Path) -> Path:
        # Expand "~" (Path does not do this automatically) and resolve to an
        # absolute path so writes never depend on the launcher's CWD.
        return Path(v).expanduser().resolve()


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
