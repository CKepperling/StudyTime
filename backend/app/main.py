from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.flashcards import router as flashcards_router
from app.api.notes import router as notes_router
from app.api.practice_tests import router as practice_tests_router
from app.api.progress import router as progress_router

app = FastAPI(title="StudyTime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is what actually turns the routes defined in api/auth.py into
# real, reachable endpoints - without this, /auth/signup and
# /auth/login exist in code but don't respond to anything.
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(notes_router)
app.include_router(flashcards_router)
app.include_router(progress_router)
app.include_router(practice_tests_router)


@app.get("/health")
def health():
    return {"status": "ok"}