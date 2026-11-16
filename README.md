# LinkedIn & Blog Content Studio

A small, end-to-end AI writing app that turns a brief into an editable LinkedIn
post and a longer blog article. It uses Google Gemini for generation, validates
the structured response, and lets you download individual drafts or a combined
Markdown file. Nothing is published automatically.

## Features

- One brief produces a LinkedIn post, hashtags, blog title, meta description,
  article, and key takeaways.
- The LinkedIn post and blog are generated sequentially to reduce simultaneous
  API load; each can use a separately configured Gemini model.
- Audience, tone, objective, keywords, call to action, and target article length
  guide the drafts.
- Drafts can be edited in the app before downloading.
- API credentials are read from the environment, never displayed or stored in
  the app's session state.
- Provider failures are logged on the server and shown as recoverable messages.

## Run locally

Requires Python 3.11 or newer.

```powershell
cd LinkedIn_Post_Generator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GOOGLE_API_KEY` in `.env`, then start the app. `GEMINI_MODEL` is the
default for both drafts; optionally set `GEMINI_LINKEDIN_MODEL` and
`GEMINI_BLOG_MODEL` to override them independently:

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit (usually <http://localhost:8501>).
Keep `.env` private; it is excluded from version control.

## Run tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

The tests do not make network or Gemini API calls.

## Run with Docker

Create `.env` with `GOOGLE_API_KEY`, then:

```powershell
docker build -t content-studio .
docker run --rm --env-file .env -p 8501:8501 content-studio
```

For a production deployment, provide the API key through your platform's secret
manager, terminate TLS at a trusted reverse proxy, and restrict access to the
app as appropriate. Do not bake credentials into the image.

## Data and limitations

The brief and generation request are sent to Google's Gemini API. Generated
drafts remain in the current Streamlit session and are not written to a
database. Review all claims, sources, and tone before publishing; the model can
make mistakes. This app does not connect to LinkedIn and cannot publish posts.

## Project layout

```text
app.py
content_studio/
  config.py       Environment configuration
  generator.py    Gemini integration and generation errors
  models.py       Validated request and response schemas
  prompts.py      Writing instructions
tests/
  test_content.py
```
