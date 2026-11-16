from __future__ import annotations

import pytest
from pydantic import ValidationError

from content_studio.config import Settings
from content_studio.exports import (
    format_hashtags,
    render_blog_markdown,
    render_combined_markdown,
)
from content_studio.generator import ContentGenerator, GenerationError
from content_studio.models import BlogDraft, ContentRequest, GeneratedContent, LinkedInDraft
from content_studio.prompts import build_blog_prompt, build_linkedin_prompt, build_user_prompt


def valid_request(**overrides: object) -> ContentRequest:
    values: dict[str, object] = {
        "brief": "Explain how small teams can make code reviews more useful and kind.",
        "audience": "Software developers on small teams",
        "tone": "Clear and practical",
        "objective": "Share a useful perspective",
    }
    values.update(overrides)
    return ContentRequest(**values)


def valid_generated_content(**overrides: object) -> GeneratedContent:
    values: dict[str, object] = {
        "linkedin_post": "A useful code review is a conversation, not a scorecard. " * 2,
        "hashtags": ["#Engineering", "CodeReview"],
        "blog_title": "Make Code Reviews More Useful",
        "meta_description": "Practical ways to make code reviews clearer and kinder.",
        "blog_markdown": "## Start with context\n\n" + ("Explain the change and its trade-offs. " * 8),
        "key_takeaways": ["Lead with context", "Be specific", "Discuss trade-offs"],
    }
    values.update(overrides)
    return GeneratedContent(**values)


def install_fake_gemini_models(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[type, dict[str, object]],
    failed_model: str | None = None,
) -> list[tuple[str, type]]:
    calls: list[tuple[str, type]] = []

    def fake_chat_google_generative_ai(**kwargs: object) -> object:
        model_name = str(kwargs["model"])

        class FakeChatModel:
            def with_structured_output(self, schema: type, method: str) -> object:
                class FakeStructuredModel:
                    def invoke(self, _messages: object) -> dict[str, object]:
                        calls.append((model_name, schema))
                        if model_name == failed_model:
                            raise RuntimeError("simulated provider failure")
                        return responses[schema]

                return FakeStructuredModel()

        return FakeChatModel()

    monkeypatch.setattr(
        "content_studio.generator.ChatGoogleGenerativeAI",
        fake_chat_google_generative_ai,
    )
    return calls


def test_request_rejects_too_short_brief() -> None:
    with pytest.raises(ValidationError):
        valid_request(brief="Too short")


def test_request_enforces_blog_length_range() -> None:
    with pytest.raises(ValidationError):
        valid_request(blog_word_count=2_000)


def test_prompt_includes_all_user_requirements() -> None:
    request = valid_request(keywords="code review, collaboration", call_to_action="Share a tip")

    prompt = build_user_prompt(request)

    assert request.brief in prompt
    assert request.audience in prompt
    assert "code review, collaboration" in prompt
    assert "Share a tip" in prompt
    assert "800 words" in prompt


def test_draft_prompts_keep_requirements_separate() -> None:
    request = valid_request()

    assert "LinkedIn post" in build_linkedin_prompt(request)
    assert "hashtags" in build_linkedin_prompt(request)
    assert "800 words" in build_blog_prompt(request)
    assert "key takeaways" in build_blog_prompt(request)


def test_settings_allow_independent_model_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "shared-model")
    monkeypatch.delenv("GEMINI_LINKEDIN_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_BLOG_MODEL", raising=False)

    settings = Settings.from_environment()

    assert settings.linkedin_model_name == "shared-model"
    assert settings.blog_model_name == "shared-model"

    monkeypatch.setenv("GEMINI_LINKEDIN_MODEL", "linkedin-model")
    monkeypatch.setenv("GEMINI_BLOG_MODEL", "blog-model")

    settings = Settings.from_environment()

    assert settings.linkedin_model_name == "linkedin-model"
    assert settings.blog_model_name == "blog-model"


def test_generator_runs_model_calls_sequentially_and_combines_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        LinkedInDraft: {
            "linkedin_post": "A useful code review is a conversation, not a scorecard. " * 2,
            "hashtags": ["#Engineering"],
        },
        BlogDraft: {
            "blog_title": "Make Code Reviews More Useful",
            "meta_description": "Practical ways to make code reviews clearer and kinder.",
            "blog_markdown": "## Start with context\n\n"
            + ("Explain the change and its trade-offs. " * 8),
            "key_takeaways": ["Lead with context", "Be specific", "Discuss trade-offs"],
        },
    }
    calls = install_fake_gemini_models(monkeypatch, responses)
    generated = ContentGenerator(
        api_key="test-key",
        model_name="shared-model",
        linkedin_model_name="linkedin-model",
        blog_model_name="blog-model",
    ).generate(valid_request())

    assert calls == [
        ("linkedin-model", LinkedInDraft),
        ("blog-model", BlogDraft),
    ]
    assert generated.blog_title == "Make Code Reviews More Useful"
    assert generated.hashtags == ["#Engineering"]


def test_generator_identifies_the_failed_draft(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    responses = {
        LinkedInDraft: {
            "linkedin_post": "A useful code review is a conversation, not a scorecard. " * 2,
            "hashtags": ["#Engineering"],
        },
        BlogDraft: {
            "blog_title": "Make Code Reviews More Useful",
            "meta_description": "Practical ways to make code reviews clearer and kinder.",
            "blog_markdown": "## Start with context\n\n"
            + ("Explain the change and its trade-offs. " * 8),
            "key_takeaways": ["Lead with context", "Be specific", "Discuss trade-offs"],
        },
    }
    calls = install_fake_gemini_models(
        monkeypatch,
        responses,
        failed_model="blog-model",
    )
    generator = ContentGenerator(
        api_key="test-key",
        model_name="shared-model",
        linkedin_model_name="linkedin-model",
        blog_model_name="blog-model",
    )

    with pytest.raises(GenerationError, match="blog draft"):
        generator.generate(valid_request())

    assert calls == [
        ("linkedin-model", LinkedInDraft),
        ("blog-model", BlogDraft),
    ]
    assert "blog draft generation failed for model blog-model" in caplog.text


def test_generated_content_requires_minimum_takeaways() -> None:
    with pytest.raises(ValidationError):
        valid_generated_content(key_takeaways=["Only one"])


def test_generated_content_rejects_empty_takeaways_after_cleanup() -> None:
    with pytest.raises(ValidationError):
        valid_generated_content(key_takeaways=["One", " ", "One"])


def test_export_helpers_preserve_edits_and_format_hashtags() -> None:
    tags = format_hashtags(["#AI", "Content Strategy", "", "ai"])
    blog = render_blog_markdown(
        "Edited title",
        "Edited meta description for the article.",
        "## Edited section\n\nEdited article body.",
        ["Edited takeaway"],
    )
    combined = render_combined_markdown("Edited post", tags, blog)

    assert tags == "#AI #ContentStrategy"
    assert "# Edited title" in blog
    assert "Edited article body." in combined
    assert "Edited post" in combined
