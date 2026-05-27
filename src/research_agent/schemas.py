from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["web", "docs", "github", "codebase"]


class AudienceRole(str, Enum):
    developer = "developer"
    hr = "hr"
    sales = "sales"
    devops = "devops"
    qa = "qa"
    general = "general"


class SkillLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    na = "na"


class AudienceProfile(BaseModel):
    role: AudienceRole = AudienceRole.developer
    skill_level: SkillLevel = SkillLevel.intermediate
    tone: Literal["technical", "plain"] = "technical"


class IntentSpec(BaseModel):
    target: str = Field(description="Technology / library / service being integrated")
    source_stack: str = Field(default="", description="User's existing language or runtime")
    frameworks: list[str] = Field(default_factory=list)
    domain: str = Field(default="", description="High-level domain (DeFi, auth, billing, ...)")
    task_type: Literal["integration", "migration", "evaluation"] = "integration"
    constraints: list[str] = Field(default_factory=list)
    audience: AudienceProfile = Field(default_factory=AudienceProfile)


class ResearchPlan(BaseModel):
    sub_questions: list[str] = Field(default_factory=list)
    web_queries: list[str] = Field(default_factory=list)
    docs_urls: list[str] = Field(default_factory=list)
    github_queries: list[str] = Field(default_factory=list)
    notes: str = ""


class ResearchFinding(BaseModel):
    id: str
    source_type: SourceType
    url: str = ""
    title: str = ""
    snippet: str = ""
    content: str = ""
    warnings: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ManifestInfo(BaseModel):
    path: str
    kind: str
    dependencies: dict[str, str] = Field(default_factory=dict)
    scripts: dict[str, str] = Field(default_factory=dict)


class ScanResult(BaseModel):
    root_path: str
    languages: dict[str, int] = Field(default_factory=dict)
    primary_language: str | None = None
    frameworks: list[str] = Field(default_factory=list)
    manifests: list[ManifestInfo] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    directory_tree: str = ""
    file_count: int = 0
    line_count_estimate: int = 0
    readme_excerpt: str | None = None
    git_remote: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Chunk(BaseModel):
    id: str
    text: str
    source_id: str
    heading_path: str = ""
    token_estimate: int = 0


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float
    matched_query: str


class ReportSection(BaseModel):
    id: str
    title: str
    body_markdown: str
    citations: list[str] = Field(default_factory=list)


class ReportMetadata(BaseModel):
    title: str
    slug: str
    created_at: datetime
    path: str
    query: str
