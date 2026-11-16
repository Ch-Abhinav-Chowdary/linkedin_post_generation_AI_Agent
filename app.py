"""Streamlit interface for the LinkedIn and blog content studio."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from content_studio.config import Settings
from content_studio.exports import (
    format_hashtags,
    render_blog_markdown,
    render_combined_markdown,
)
from content_studio.generator import ContentGenerator, GenerationError
from content_studio.models import ContentRequest

LOGGER = logging.getLogger(__name__)
load_dotenv(Path(__file__).with_name(".env"), override=False)

st.set_page_config(
    page_title="Content Studio",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { --ink:#e9edf7; --muted:#a3aec2; --line:rgba(170,190,225,.15); }
    .stApp {
        background: radial-gradient(ellipse at 10% 0%,rgba(77,102,181,.20),transparent 35rem),
                    radial-gradient(ellipse at 95% 15%,rgba(39,156,141,.13),transparent 30rem),
                    #0b1020;
        color:var(--ink); font-family:'DM Sans',sans-serif;
    }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:rgba(12,17,33,.93); border-right:1px solid var(--line); }
    .hero { padding:2.4rem 0 1.4rem; }
    .eyebrow { color:#78e7d7; font-size:.75rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
    .hero h1 { margin:.35rem 0; color:#f0f2fb; font:800 clamp(2rem,5vw,3.4rem)/1.1 'Manrope',sans-serif; letter-spacing:-.055em; }
    .hero p, .muted { color:var(--muted); line-height:1.7; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line); border-radius:1rem; }
    div.stButton > button, div.stDownloadButton > button { border-radius:.7rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = Settings.from_environment()
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">One brief · two ready-to-edit drafts</div>
      <h1>Content Studio</h1>
      <p>Turn your idea into a professional LinkedIn post and a thoughtful,
      structured blog article. Review every claim before publishing.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not settings.api_key:
    st.warning(
        "Generation is unavailable until `GOOGLE_API_KEY` is configured in the "
        "environment or this project's `.env` file."
    )

with st.form("content_brief"):
    st.subheader("Your brief")
    brief = st.text_area(
        "What should the content be about?",
        placeholder=(
            "Describe the idea, your experience, and the points you want to make. "
            "Include source facts if you want them reflected."
        ),
        height=160,
        max_chars=8_000,
        help="Use at least 30 characters. Avoid including confidential information.",
    )

    left, right = st.columns(2)
    with left:
        audience = st.text_input("Target audience", placeholder="e.g. early-career data analysts")
        tone = st.selectbox(
            "Tone",
            ["Clear and practical", "Thought leadership", "Conversational", "Warm and encouraging", "Analytical"],
        )
        objective = st.text_input(
            "Primary objective",
            value="Share a useful perspective and build credibility",
        )
        language = st.text_input("Output language", value="English", max_chars=60)
    with right:
        keywords = st.text_input(
            "Keywords (optional)",
            placeholder="Comma-separated; used naturally where relevant",
            max_chars=500,
        )
        call_to_action = st.text_input(
            "Call to action (optional)",
            placeholder="e.g. Ask readers to share their experience",
            max_chars=500,
        )
        blog_word_count = st.slider("Target blog length", 500, 1_800, 800, step=100)

    submitted = st.form_submit_button(
        "Generate both drafts",
        type="primary",
        use_container_width=True,
        disabled=not settings.api_key,
    )

if submitted:
    try:
        request = ContentRequest(
            brief=brief,
            audience=audience,
            tone=tone,
            objective=objective,
            keywords=keywords,
            call_to_action=call_to_action,
            blog_word_count=blog_word_count,
            language=language,
        )
    except ValidationError as error:
        st.error("Please check the brief and audience fields.")
        for issue in error.errors():
            location = " → ".join(str(part) for part in issue["loc"])
            st.caption(f"{location}: {issue['msg']}")
    else:
        try:
            with st.spinner("Drafting your LinkedIn post and blog article…"):
                generated = ContentGenerator(
                    api_key=settings.api_key,
                    model_name=settings.model_name,
                    request_timeout=settings.request_timeout,
                    retries=settings.retries,
                    linkedin_model_name=settings.linkedin_model_name,
                    blog_model_name=settings.blog_model_name,
                ).generate(request)
            st.session_state["generated_content"] = generated.model_dump()
            st.session_state["linkedin_post"] = generated.linkedin_post
            st.session_state["hashtags"] = ", ".join(generated.hashtags)
            st.session_state["blog_title"] = generated.blog_title
            st.session_state["meta_description"] = generated.meta_description
            st.session_state["blog_article"] = generated.blog_markdown
            st.session_state["key_takeaways"] = "\n".join(generated.key_takeaways)
            st.success("Drafts are ready. Edit them below before downloading.")
        except GenerationError as error:
            st.error(str(error))
        except Exception:
            LOGGER.exception("Unexpected error while preparing generated content")
            st.error("An unexpected error occurred. Check the application logs and try again.")

raw_generated = st.session_state.get("generated_content")
if isinstance(raw_generated, dict):
    st.divider()
    st.subheader("Review and edit")
    st.caption("Changes made here are included in your downloads; they are not saved to a database.")

    tab_post, tab_blog = st.tabs(["LinkedIn post", "Blog article"])
    with tab_post:
        linkedin_post = st.text_area(
            "Post text",
            key="linkedin_post",
            height=300,
            label_visibility="collapsed",
        )
        hashtags = st.text_input(
            "Hashtags (comma-separated; # is optional)",
            key="hashtags",
        )
        normalized_hashtags = format_hashtags(
            [tag.strip() for tag in hashtags.split(",") if tag.strip()]
        )
        st.caption(f"{len(linkedin_post)} characters · {len(normalized_hashtags.split()) if normalized_hashtags else 0} hashtags")
        st.download_button(
            "Download LinkedIn draft",
            data=f"{linkedin_post.strip()}\n\n{normalized_hashtags}".strip() + "\n",
            file_name="linkedin-post.txt",
            mime="text/plain",
        )

    with tab_blog:
        blog_title = st.text_input("Blog title", key="blog_title")
        meta_description = st.text_input("Meta description", key="meta_description")
        blog_article = st.text_area(
            "Blog article (Markdown)",
            key="blog_article",
            height=500,
        )
        takeaways_text = st.text_area(
            "Key takeaways (one per line)",
            key="key_takeaways",
            height=120,
        )
        takeaways = [item.strip() for item in takeaways_text.splitlines() if item.strip()]
        blog_markdown = render_blog_markdown(
            blog_title,
            meta_description,
            blog_article,
            takeaways,
        )
        st.download_button(
            "Download blog (Markdown)",
            data=blog_markdown,
            file_name="blog-article.md",
            mime="text/markdown",
        )

    current_post = st.session_state.get("linkedin_post", "")
    current_hashtags = format_hashtags(
        [
            tag.strip()
            for tag in st.session_state.get("hashtags", "").split(",")
            if tag.strip()
        ]
    )
    current_blog = render_blog_markdown(
        st.session_state.get("blog_title", ""),
        st.session_state.get("meta_description", ""),
        st.session_state.get("blog_article", ""),
        [
            item.strip()
            for item in st.session_state.get("key_takeaways", "").splitlines()
            if item.strip()
        ],
    )
    st.download_button(
        "Download both drafts",
        data=render_combined_markdown(current_post, current_hashtags, current_blog),
        file_name="content-drafts.md",
        mime="text/markdown",
        type="primary",
    )

    st.info(
        "Review generated claims and add sources where needed. Your brief is sent "
        "to Google's Gemini API; drafts stay in this browser session."
    )
