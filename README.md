# StudyTime

> Upload your lecture slides and papers. Get AI-generated summaries, flashcards, and practice tests. Review them on a spaced-repetition schedule so you study each card right before you'd forget it.

Built for CS 3704 at Virginia Tech.

## Team

| Name | PID | Email | GitHub |
|---|---|---|---|
| Clayton Kepperling | ckepperling86 | ckepperling86@vt.edu | [@CKepperling](https://github.com/CKepperling) |
| Tristan Livingood | tscottlivingood3 | tscottlivingood3@vt.edu | [@TristanLivingood](https://github.com/TristanLivingood) |

## The Problem

Students accumulate hundreds of pages of lecture slides, notes, and readings each semester, but rarely revisit them in a way that builds long-term retention. Existing tools only solve pieces of the problem: PDF readers don't summarize, summarizers don't quiz you, and flashcard apps (Anki, Quizlet) make you write every card by hand. There is no single tool that takes raw course material in and produces a structured, spaced-repetition-ready study system out.

## What StudyTime Does

1. **Upload** a PDF (lecture slides, notes, or a paper). Text is extracted in the background.
2. **Summarize** the material at three difficulty levels.
3. **Generate flashcards** from the key concepts, or write your own by hand.
4. **Review** due cards using the SM-2 spaced-repetition algorithm. Each grade you give reschedules the card.
5. **Practice** with an AI-generated multiple-choice test and get scored instantly (tests can be retaken freely).
6. **Take notes** on any document.
7. **Track progress** on a dashboard: documents, flashcards, cards due now, cards mastered, reviews today and over the last 7 days, 7-day accuracy, and your current daily streak.

You can also delete a document, which removes everything generated from it.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 |
| Background jobs | Celery + Redis (PDF extraction and AI generation) |
| AI | Google Gemini API (`google-genai` SDK) |
| Auth | JWT (`python-jose`), bcrypt password hashing |
| Frontend | React 19 + Vite, React Router |
| Containers | Docker + Docker Compose |
| CI | GitHub Actions (ruff, pytest, frontend lint and build) |

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────────┐
│  React UI   │─────▶│  FastAPI API │─────▶│  PostgreSQL DB   │
└─────────────┘      └──────┬───────┘      └──────────────────┘
                            │ enqueue
                            ▼
                     ┌─────────────┐      ┌──────────────────┐
                     │    Redis    │─────▶│  Celery Worker   │
                     └─────────────┘      └────────┬─────────┘
                                                   │
                                      ┌────────────┴────────────┐
                                      ▼                         ▼
                              PDF text extraction        Google Gemini API
                                 (pypdf)            (summaries, flashcards, tests)
```

## Getting Started

### Dependencies

You only need these installed on your machine:

- **Git**
- **Docker Desktop** (includes Docker Compose v2): https://www.docker.com/products/docker-desktop
- **A Google Gemini API key** (the free tier is enough): https://aistudio.google.com/apikey
- **OpenSSL** (preinstalled on macOS and most Linux) to generate a secret key. Any long random string works if you don't have it.

Everything else is installed automatically inside the containers:

- Python packages are listed in [`backend/requirements.txt`](backend/requirements.txt) (FastAPI, SQLAlchemy, Alembic, Celery, Redis client, pypdf, google-genai, and others).
- JavaScript packages are listed in [`frontend/package.json`](frontend/package.json) (React, React Router, Vite).
- Runtime images: `python:3.12-slim`, `node:20-slim`, `postgres:16`, `redis:7`.

### Run it

**1. Clone the repo**

```bash
git clone https://github.com/CKepperling/StudyTime.git
cd StudyTime
```

**2. Create your `.env` file**

```bash
cp .env.example .env
```

Open `.env` and set two values:

- `GEMINI_API_KEY`: paste your key from Google AI Studio.
- `SECRET_KEY`: generate one with `openssl rand -hex 32` and paste the output.

The other defaults work as-is for Docker (see [Environment Variables](#environment-variables)).

**3. Build and start everything**

```bash
docker compose -f Docker-compose.yml up --build
```

The `-f` flag matters: the file is named `Docker-compose.yml` (capital D), which Docker only finds automatically on case-insensitive filesystems like macOS.

**4. Create the database tables (first run only)**

Wait until the logs show the backend is running, then in a second terminal:

```bash
docker compose -f Docker-compose.yml exec backend alembic upgrade head
```

The app does not create tables on startup, so skip this and sign-up will fail with a "relation does not exist" error.

**5. Open the app**

| What | URL |
|---|---|
| Web app | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

To stop everything, press `Ctrl+C` and run `docker compose -f Docker-compose.yml down`. Add `-v` to also wipe the database.

### Using the app

1. Go to http://localhost:5173 and **sign up** with an email and password.
2. On **Documents**, choose a PDF and click **Upload**. Wait for its status to change to `extracted`.
3. Click the document. From there you can **Generate summaries**, **Generate practice test**, open **Notes**, or open **View flashcards** and click **Generate flashcards with AI**.
4. Open **Review queue** to review due cards and grade yourself.
5. Open **Progress** to see your stats.

AI generation is **manual by default** to conserve free-tier Gemini quota. To generate everything automatically after upload, set the three `AUTO_GENERATE_*` variables to `true` in `.env` and restart.

## Environment Variables

All of these live in `.env` at the repo root (copy from `.env.example`).

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key. |
| `SECRET_KEY` | Yes | Signs login tokens. Generate with `openssl rand -hex 32`. |
| `DATABASE_URL` | Yes | Postgres connection string. Default points at the `postgres` Docker service. |
| `REDIS_URL` | Yes | Redis connection string. Default points at the `redis` Docker service. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Yes | Credentials for the Postgres container. Must match `DATABASE_URL`. |
| `GENERATION_MODEL` | No | Gemini model used for generation. Defaults to `gemini-3.5-flash-lite`, which has a much higher free daily quota. Switch to a larger Flash model for better quality (e.g. for a demo). |
| `AUTO_GENERATE_SUMMARIES` | No | `true` to generate summaries automatically after upload. Default `false`. |
| `AUTO_GENERATE_FLASHCARDS` | No | `true` to generate flashcards automatically after upload. Default `false`. |
| `AUTO_GENERATE_PRACTICE_TESTS` | No | `true` to generate a practice test automatically after upload. Default `false`. |
| `UPLOAD_DIR` | No | Where uploaded PDFs are stored. Default `uploads` (inside `backend/`). |
| `CELERY_TASK_ALWAYS_EAGER` | No | `true` runs background tasks inline with no worker or Redis. Used by tests and CI. |
| `VITE_API_BASE_URL` | No | Frontend's API address. Default `http://localhost:8000`. |

## API Overview

Interactive docs with request and response schemas are at http://localhost:8000/docs. All routes except `/auth/signup`, `/auth/login`, and `/health` require a `Bearer` token.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Documents | `POST /documents`, `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}` |
| Summaries | `POST /documents/{id}/generate-summaries`, `GET /documents/{id}/summaries` |
| Flashcards | `GET/POST /documents/{id}/flashcards`, `POST /documents/{id}/generate-flashcards`, `GET /flashcards/due`, `POST /flashcards/{id}/review` |
| Practice tests | `POST /documents/{id}/generate-practice-test`, `GET /documents/{id}/practice-tests`, `GET /practice-tests/{id}`, `POST /practice-tests/{id}/submit` |
| Notes | `GET/POST /documents/{id}/notes`, `PUT/DELETE /notes/{id}` |
| Progress | `GET /progress` |

## Running Tests and Lint

Tests run against a real Postgres database and mock all Gemini calls, so no API key or quota is used.

```bash
# 1. Start only the database
docker compose -f Docker-compose.yml up -d postgres

# 2. Set up a Python 3.12 virtual environment
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt ruff

# 3. Create tables, then test and lint
export DATABASE_URL="postgresql://studytime:studytime@localhost:5432/studytime"
export SECRET_KEY="any-value" GEMINI_API_KEY="any-value" CELERY_TASK_ALWAYS_EAGER=true
alembic upgrade head
pytest
ruff check .
```

The frontend has its own checks:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

GitHub Actions runs all of the above on every push and pull request to `main`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `no configuration file provided: not found` | Docker can't find `Docker-compose.yml`. Add `-f Docker-compose.yml` to the command. |
| `relation "users" does not exist` on sign-up | Run step 4: `docker compose -f Docker-compose.yml exec backend alembic upgrade head`. |
| `variable is not set` warnings or a Postgres crash on startup | `.env` is missing or incomplete. Re-copy it from `.env.example`. |
| Generation fails with a quota or 429 error | You've hit the Gemini free-tier limit. Keep `GENERATION_MODEL` on the flash-lite model or wait for the daily reset. |
| Document stuck on `pending` | The worker isn't running. Check `docker compose -f Docker-compose.yml logs worker`. |
| Browser shows a network or CORS error | The API only allows requests from http://localhost:5173. Open the app at exactly that address. |
| Port 5173, 8000, 5432, or 6379 already in use | Stop the local service using it, or change the port mapping in `Docker-compose.yml`. |

## Project Structure

```
StudyTime/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes: auth, documents, flashcards, notes, practice_tests, progress
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Gemini generation, SM-2 scheduling, progress stats, auth
│   │   ├── workers/       # Celery app and background tasks
│   │   ├── db.py, storage.py, main.py
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/           # Backend API client
│   │   ├── components/    # Layout, auth form, protected route
│   │   ├── context/       # Auth state
│   │   └── pages/         # Home, Login, Signup, DocumentDetail, FlashcardList, Notes, Review, PracticeTest, Progress
│   ├── package.json
│   └── Dockerfile
├── .github/workflows/ci.yml
├── Docker-compose.yml
├── .env.example
└── README.md
```

## Contributing

- Work on a branch prefixed with its ticket number, and open a pull request into `main`.
- CI (lint, tests, build) must pass before merging.
- Don't commit `.env` or anything under `backend/uploads/`; both are gitignored.

AI tool usage on this project follows the course [AI Policy](https://github.com/CS3704-VT/Course/blob/main/AI_POLICY.md).