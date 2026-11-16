"""Validated input and output types for a content generation request."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brief: str = Field(min_length=30, max_length=8_000)
    audience: str = Field(min_length=2, max_length=300)
    tone: str = Field(min_length=2, max_length=80)
    objective: str = Field(min_length=2, max_length=300)
    keywords: str = Field(default="", max_length=500)
    call_to_action: str = Field(default="", max_length=500)
    blog_word_count: int = Field(default=800, ge=500, le=1_800)
    language: str = Field(default="English", min_length=2, max_length=60)


class LinkedInDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    linkedin_post: str = Field(min_length=50, max_length=5_000)
    hashtags: list[str] = Field(default_factory=list, max_length=5)


class BlogDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    blog_title: str = Field(min_length=5, max_length=180)
    meta_description: str = Field(min_length=20, max_length=300)
    blog_markdown: str = Field(min_length=200, max_length=30_000)
    key_takeaways: list[str] = Field(min_length=3, max_length=5)


class GeneratedContent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    linkedin_post: str = Field(min_length=50, max_length=5_000)
    hashtags: list[str] = Field(default_factory=list, max_length=5)
    blog_title: str = Field(min_length=5, max_length=180)
    meta_description: str = Field(min_length=20, max_length=300)
    blog_markdown: str = Field(min_length=200, max_length=30_000)
    key_takeaways: list[str] = Field(min_length=3, max_length=5)

    @field_validator("linkedin_post", "blog_title", "meta_description", "blog_markdown")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Generated text must not be empty.")
        return value.strip()

    @field_validator("hashtags")
    @classmethod
    def strip_and_deduplicate_hashtags(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            normalized = item.casefold()
            if item and normalized not in seen:
                cleaned.append(item)
                seen.add(normalized)
        return cleaned

    @field_validator("key_takeaways")
    @classmethod
    def require_unique_takeaways(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            normalized = item.casefold()
            if item and normalized not in seen:
                cleaned.append(item)
                seen.add(normalized)
        if len(cleaned) < 3:
            raise ValueError("At least three non-empty, unique key takeaways are required.")
        return cleaned
