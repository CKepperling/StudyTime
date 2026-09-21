# This file exists so importing `app.models` pulls in every model at once.
# Alembic's autogenerate can only "see" tables whose model class has
# actually been imported somewhere - a model file that's never imported
# here (or elsewhere) is invisible to it and silently skipped.

from app.models.user import User
from app.models.document import Document
from app.models.summary import Summary, DifficultyLevel
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.note import Note
from app.models.practice_test import PracticeTest, TestQuestion
from app.models.review_log import ReviewLog