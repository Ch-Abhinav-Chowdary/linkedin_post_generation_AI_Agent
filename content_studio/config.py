"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-3.8-flash"


@dataclass(frozen=True)
class Settings:
    """Runtime settings that do not contain user-entered content."""

    api_key: str
    model_name: str = DEFAULT_MODEL
    linkedin_model_name: str = DEFAULT_MODEL
    blog_model_name: str = DEFAULT_MODEL
    request_timeout: float = 90.0
    retries: int = 2

    @classmethod
    def from_environment(cls) -> Settings:
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        return cls(
            api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
            model_name=model_name,
            linkedin_model_name=(
                os.getenv("GEMINI_LINKEDIN_MODEL", "").strip() or model_name
            ),
            blog_model_name=os.getenv("GEMINI_BLOG_MODEL", "").strip() or model_name,
        )
