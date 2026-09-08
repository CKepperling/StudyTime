# StudyTime

> Upload your lecture notes and papers. Get AI-generated summaries and flashcards. Review them with spaced repetition, backed by a system that actually knows what you've forgotten.

## The Problem

Students accumulate hundreds of pages of lecture slides, notes, and readings per semester but rarely revisit them in a way that builds long-term retention. Existing tools solve pieces of this in isolation: PDF readers don't summarize, summarizers don't quiz you, and flashcard apps (Anki, Quizlet) require you to manually author every card. There's no single tool that takes raw course material in, and produces a structured, retrievable, spaced-repetition-ready study system out.

## What It Does

1. **Upload** a PDF (lecture slides, notes, or a paper).
2. **Summarize** — the system extracts text and generates a concise, structured summary of the material.
3. **Generate flashcards** — key concepts are turned into question/answer pairs automatically.
4. **Review** — flashcards are scheduled using the SM-2 spaced-repetition algorithm, so you review things right before you'd forget them.
5. **Track progress** — a dashboard shows what's due, retention trends, and per-document mastery.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | PostgreSQL |
| Background jobs | Celery + Redis (PDF processing, summarization) |
| AI / LLM | Anthropic API (summarization + flashcard generation) |
| Frontend | React (Vite) |
| Containerization | Docker + Docker Compose |
| CI | GitHub Actions |

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────────┐
│   React UI  │─────▶│  FastAPI API │─────▶│   PostgreSQL DB   │
└─────────────┘      └──────┬───────┘      └──────────────────┘
                             │
                             ▼
                     ┌───────────────┐      ┌─────────────────┐
                     │ Celery Worker │─────▶│  Anthropic API   │
                     └───────────────┘      └─────────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │    Redis    │
                      └─────────────┘
```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- An Anthropic API key (or your chosen LLM provider's key)

### Setup

```bash
git clone https://github.com/<org>/StudyTime.git
cd StudyTime
cp .env.example .env   # add your API key and DB credentials
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

### Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `ANTHROPIC_API_KEY` | LLM provider API key |
| `SECRET_KEY` | Auth/session signing key |

## Project Structure

```
StudyTime/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # summarization, flashcard gen, SM-2 logic
│   │   ├── workers/       # Celery tasks
│   │   └── main.py
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Roadmap

- [ ] PDF upload & text extraction
- [ ] AI-generated summaries
- [ ] AI-generated flashcards
- [ ] SM-2 spaced repetition review loop
- [ ] Progress dashboard
- [ ] User accounts / multi-user support
- [ ] Support for non-PDF sources (slides exported as images, raw text paste)

## Team & Contributing

| Name | Role |
|---|---|
| — | — |
| — | — |

See `CONTRIBUTING.md` for branch naming, commit conventions, and PR review process. See `TEAM_POLICY.md` for our team's meeting cadence and AI usage policy (per course [AI Policy](https://github.com/CS3704-VT/Course/blob/main/AI_POLICY.md)).

## License

MIT (or your team's choice — update before submission).