"""Pydantic data models for ResearchBot."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskType(str, Enum):
    """Research task types."""
    INITIAL = "initial"
    TARGETED = "targeted"
    DRAFT = "draft"


class ModeType(str, Enum):
    """Query mode types."""
    AUTO = "auto"
    MANUAL = "manual"


class PlatformType(str, Enum):
    """AI platform types."""
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    CHATGPT = "chatgpt"


class UploadedFile(BaseModel):
    """Represents an uploaded file."""
    filename: str
    path: str
    file_type: str
    size_bytes: int
    upload_time: datetime = Field(default_factory=datetime.now)

    @field_validator("size_bytes")
    @classmethod
    def validate_size(cls, v: int) -> int:
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f"File too large. Maximum size is 50MB, got {v / (1024*1024):.2f}MB")
        return v


class UserQuery(BaseModel):
    """Represents a user research query."""
    session_id: str
    query_text: str
    files: List[UploadedFile] = Field(default_factory=list)
    model_choice: str = "auto"
    mode: ModeType = ModeType.AUTO
    task: TaskType = TaskType.INITIAL
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("files")
    @classmethod
    def validate_file_count(cls, v: List[UploadedFile]) -> List[UploadedFile]:
        if len(v) > 5:
            raise ValueError(f"Maximum 5 files allowed, got {len(v)}")
        return v


class PlatformResponse(BaseModel):
    """Represents a response from an AI platform."""
    platform: PlatformType
    query_id: str
    response_text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_used: Optional[int] = None
    error: Optional[str] = None


class MergedResponse(BaseModel):
    """Represents merged responses from multiple platforms."""
    session_id: str
    query_id: str
    original_responses: List[PlatformResponse] = Field(default_factory=list)
    merged_text: str
    structure: dict = Field(default_factory=dict)
    attribution: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("merged_text")
    @classmethod
    def validate_merged_text(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("Merged response too short. Minimum 50 characters required.")
        if len(v) > 50000:
            raise ValueError("Merged response too long. Maximum 50,000 characters allowed.")
        return v
