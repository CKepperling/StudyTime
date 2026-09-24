# StudyTime

> Upload your lecture notes and papers. Get AI-generated summaries, flashcards, and practice tests. Review flashcards with spaced repetition, backed by a system that actually knows what you've forgotten.

## What It Does

1. **Sign up / log in** — JWT-based auth; every document, note, flashcard, and test belongs to one user and is never visible to another.
2. **Upload** a PDF (lecture slides, notes, or a paper).
3. **Extraction** — a background worker pulls the raw text out of the PDF automatically after upload.
4. **Summarize** — generate a summary at easy, medium, or hard reading level (one Gemini call per level), and switch between them on the document page.
5. **Generate flashcards** — key concepts are turned into question/answer pairs automatically, or add your own by hand.
6. **Review** — flashcards are scheduled using the SM-2 spaced-repetition algorithm, so you review things right before you'd forget them.
7. **Practice tests** — generate a short-answer test from a document, take it, and get it graded instantly with a per-question breakdown.
8. **Quick notes** — a simple freeform notes panel on each document, independent of anything AI-generated.
9. **Track progress** — a dashboard shows what's due, retention trends, and totals across everything you've studied.
10. **Delete a document** — removes it and everything generated from it (summaries, flashcards, notes, practice tests, and their own review history) in one action.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI |
| Database | PostgreSQL (SQLAlchemy 2.0 + Alembic migrations) |
| Background jobs | Celery + Redis (PDF extraction, AI generation) |
| AI / LLM | Google Gemini API (`google-genai`) |
| Auth | JWT (`python-jose`) + bcrypt password hashing |
| Frontend | React (Vite) |
| Containerization | Docker + Docker Compose |
| CI | GitHub Actions (backend: ruff + pytest against a real Postgres service; frontend: lint + build) |

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────────┐
│   React UI  │─────▶│  FastAPI API │─────▶│   PostgreSQL DB   │
└─────────────┘      └──────┬───────┘      └──────────────────┘
                             │
                             ▼
                     ┌───────────────┐      ┌─────────────────┐
                     │ Celery Worker │─────▶│   Gemini API     │
                     └───────┬───────┘      └─────────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │    Redis    │
                      └─────────────┘
```

The worker handles two kinds of background work: PDF text extraction (runs automatically after every upload) and AI generation (summaries, flashcards, practice tests — triggered manually from the UI by default; see `AUTO_GENERATE_SUMMARIES` below for why).

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python **3.12** locally if you'll run backend commands (tests, migrations) outside Docker — the backend image is built on 3.12, and some dependencies used here require 3.10+
- A free [Google AI Studio](https://aistudio.google.com/) API key for Gemini

### Setup

```bash
git clone https://github.com/CKepperling/StudyTime.git
cd StudyTime
cp .env.example .env   # fill in a real SECRET_KEY and GEMINI_API_KEY
docker compose -f Docker-compose.yml up --build
```

> Note the compose file here is named `Docker-compose.yml` (capital D), not the more common lowercase `docker-compose.yml` — pass `-f Docker-compose.yml` explicitly, or just `docker compose up --build` on macOS, where the filesystem is case-insensitive and finds it either way. Linux users and CI need the explicit `-f` flag.

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

### Environment Variables

All of these live in `.env` (copy `.env.example` to start) and are documented inline there too.

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string (use service name `postgres` as host, not `localhost`, so containers can reach each other) |
| `REDIS_URL` | Redis connection string, used as the Celery broker |
| `GEMINI_API_KEY` | Your Google AI Studio API key |
| `GENERATION_MODEL` | Which Gemini model to call. Defaults to a Flash-Lite model — the team's free-tier key is capped at a tight daily request quota on full Flash models, and Lite gets a much higher daily allowance. Switch to a current full Flash model before a demo. |
| `AUTO_GENERATE_SUMMARIES` | `true`/`false`. When `false` (the default), summaries/flashcards/practice tests only generate when explicitly triggered from the UI ("Generate summaries" etc.), to conserve the daily Gemini quota during development. Set to `true` for automatic generation right after upload — nicer for a demo. |
| `SECRET_KEY` | Signs JWTs. Generate with `openssl rand -hex 32` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Used by the Postgres container itself on first init |

## Project Structure

```
StudyTime/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   │   ├── auth.py           # signup, login, /auth/me
│   │   │   ├── documents.py      # upload, list/get/delete, and every
│   │   │   │                     #   document-scoped sub-resource
│   │   │   │                     #   (flashcards, summaries, practice
│   │   │   │                     #   tests, generation triggers)
│   │   │   ├── flashcards.py     # due queue + SM-2 review submission
│   │   │   ├── notes.py          # notes CRUD
│   │   │   ├── practice_tests.py # take a test, submit + grade
│   │   │   ├── progress.py       # dashboard stats
│   │   │   └── deps.py           # get_current_user dependency
│   │   ├── models/         # SQLAlchemy models (one file per table)
│   │   ├── schemas/        # Pydantic request/response shapes
│   │   ├── services/       # business logic with no FastAPI dependency:
│   │   │   ├── auth.py               # password hashing, JWT
│   │   │   ├── generation.py         # shared Gemini call + schema
│   │   │   │                         #   validation, everything AI-
│   │   │   │                         #   generated is built on this
│   │   │   ├── summary.py            # per-level summary prompts
│   │   │   ├── flashcard_generation.py
│   │   │   ├── practice_test_generation.py
│   │   │   ├── sm2.py                # spaced-repetition scheduling math
│   │   │   └── progress.py           # dashboard aggregation queries
│   │   ├── workers/        # Celery app + tasks (extraction, all
│   │   │                   #   three generation types)
│   │   ├── storage.py      # shared UPLOAD_DIR definition
│   │   └── main.py
│   ├── alembic/            # migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/            # one file per backend resource, all built
│   │   │                   #   on api/client.js's shared apiFetch
│   │   ├── components/     # Layout, ProtectedRoute, AuthForm
│   │   ├── context/        # AuthContext (token + current user state)
│   │   └── pages/          # Home, DocumentDetail, FlashcardList,
│   │                       #   Notes, PracticeTest, Review, Progress,
│   │                       #   Login, Signup
│   └── Dockerfile
├── .github/workflows/ci.yml
├── Docker-compose.yml
├── .env.example
└── README.md
```

## Running Tests

The backend test suite needs several environment variables set that Docker normally provides automatically — when running `pytest` directly (not through Docker), set them inline:

```bash
cd backend
source .venv/bin/activate   # a Python 3.12 venv
pip install -r requirements.txt

DATABASE_URL="postgresql://studytime:studytime@localhost:5432/studytime" \
SECRET_KEY="any-value-for-local-testing" \
GEMINI_API_KEY="any-value-unless-a-test-calls-the-real-API" \
CELERY_TASK_ALWAYS_EAGER=true \
pytest
```

(`docker compose up -d postgres` first, if Postgres isn't already running.)

Most Gemini-backed tests mock the API call rather than hitting the real service, so a real `GEMINI_API_KEY` isn't required for the suite to pass — it's still needed for the app itself to run, since `app/services/generation.py` reads it at import time.

Lint with `ruff check .` the same way, with the same environment variables set.

CI runs both automatically on every PR against `main`, using a real (throwaway) Postgres service container — see `.github/workflows/ci.yml`.

## Known Gotchas

A few things that cost real debugging time during development, worth knowing up front:

- **Python version matters.** Some dependencies here (notably `google-genai`) require Python 3.10+, and a few SQLAlchemy model type hints assume 3.10+ union syntax support. Use Python 3.12 locally to match the Docker image exactly.
- **File casing.** macOS's filesystem is case-insensitive; Linux (including GitHub Actions) is not. A local build can succeed with a file/import casing mismatch that then fails in CI. If a build fails in CI with an `UNRESOLVED_IMPORT` error that doesn't reproduce locally, check for a casing mismatch with `git ls-files | grep -i <name>`.
- **`bcrypt` is pinned to `4.0.1`**, not the latest release — `passlib==1.7.4` (the version this project uses) is incompatible with `bcrypt>=4.1`.
- **Gemini's free-tier daily quota is tight** on full Flash models (roughly 20 requests/day at time of writing) — this is why generation defaults to a Flash-Lite model and to manual triggering rather than automatic-on-upload. See `GENERATION_MODEL` and `AUTO_GENERATE_SUMMARIES` above.
- **Gemini model names change fairly often** — if a generation call 404s with a message naming a different recommended model, that's the fix: update `GENERATION_MODEL` in `.env` to whatever name the error suggests.

## License

MIT (or your team's choice — update before submission).