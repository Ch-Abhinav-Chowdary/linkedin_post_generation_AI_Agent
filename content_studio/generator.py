"""Gemini-backed generation service."""

from __future__ import annotations

import logging
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from content_studio.models import (
    BlogDraft,
    ContentRequest,
    GeneratedContent,
    LinkedInDraft,
)
from content_studio.prompts import (
    SYSTEM_PROMPT,
    build_blog_prompt,
    build_linkedin_prompt,
)

LOGGER = logging.getLogger(__name__)
DraftModel = TypeVar("DraftModel", bound=BaseModel)


class GenerationError(RuntimeError):
    """A safe, user-presentable generation failure."""


class ContentGenerator:
    """Generate a validated post and blog draft using Gemini."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        request_timeout: float = 90.0,
        retries: int = 2,
        linkedin_model_name: str | None = None,
        blog_model_name: str | None = None,
    ) -> None:
        if not api_key.strip():
            raise GenerationError("A Google AI API key is required.")
        self._api_key = api_key
        self._linkedin_model_name = linkedin_model_name or model_name
        self._blog_model_name = blog_model_name or model_name
        self._request_timeout = request_timeout
        self._retries = retries

    def generate(self, request: ContentRequest) -> GeneratedContent:
        """Generate the LinkedIn draft, then the blog, and validate their combination."""
        linkedin = self._generate_draft(
            "LinkedIn",
            self._linkedin_model_name,
            LinkedInDraft,
            build_linkedin_prompt(request),
        )
        blog = self._generate_draft(
            "blog",
            self._blog_model_name,
            BlogDraft,
            build_blog_prompt(request),
        )
        return GeneratedContent.model_validate(
            {**linkedin.model_dump(), **blog.model_dump()}
        )

    def _generate_draft(
        self,
        draft_name: str,
        model_name: str,
        output_schema: type[DraftModel],
        prompt: str,
    ) -> DraftModel:
        try:
            model = ChatGoogleGenerativeAI(
                model=model_name,
                api_key=self._api_key,
                temperature=0.7,
                max_tokens=8_192,
                request_timeout=self._request_timeout,
                retries=self._retries,
            )
            structured_model = model.with_structured_output(
                output_schema,
                method="json_schema",
            )
            result = structured_model.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            return output_schema.model_validate(result)
        except Exception as error:
            LOGGER.exception(
                "%s draft generation failed for model %s",
                draft_name,
                model_name,
            )
            raise GenerationError(
                f"Gemini could not generate the {draft_name} draft. Check the API "
                "key, model access, network connection, and service quota, then try again."
            ) from error
