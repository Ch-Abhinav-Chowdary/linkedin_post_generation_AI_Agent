"""Formatting helpers for downloading editable drafts."""

from __future__ import annotations

from content_studio.models import GeneratedContent


def format_hashtags(hashtags: list[str]) -> str:
    """Format hashtags consistently without duplicating an existing # prefix."""
    formatted = []
    seen: set[str] = set()
    for hashtag in hashtags:
        cleaned = hashtag.strip().lstrip("#").replace(" ", "")
        if cleaned and cleaned.casefold() not in seen:
            formatted.append(f"#{cleaned}")
            seen.add(cleaned.casefold())
    return " ".join(formatted)


def render_blog_markdown(
    title: str,
    meta_description: str,
    article: str,
    key_takeaways: list[str],
) -> str:
    """Build a shareable Markdown file from the currently edited fields."""
    takeaways = "\n".join(f"- {item.strip()}" for item in key_takeaways if item.strip())
    return (
        f"# {title.strip()}\n\n"
        f"> **Meta description:** {meta_description.strip()}\n\n"
        f"{article.strip()}\n\n"
        f"## Key takeaways\n\n{takeaways}\n"
    )


def render_combined_markdown(
    linkedin_post: str,
    hashtags: str,
    blog_markdown: str,
) -> str:
    """Combine the current post and article into a single Markdown download."""
    post = linkedin_post.strip()
    tag_line = hashtags.strip()
    post_section = f"{post}\n\n{tag_line}\n\n" if tag_line else f"{post}\n\n"
    return (
        "# LinkedIn post\n\n"
        f"{post_section}---\n\n{blog_markdown.strip()}\n"
    )
