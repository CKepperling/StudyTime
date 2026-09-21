# This file exists so importing `app.models` pulls in every model at once.
# Alembic's autogenerate can only "see" tables whose model class has
# actually been imported somewhere - a model file that's never imported
# here (or elsewhere) is invisible to it and silently skipped.
#
# `as X` on each import (a "redundant alias") is ruff's recommended way
# to mark a re-export as intentional, so it doesn't flag these as unused
# imports (F401) even though nothing in THIS file calls them directly.

from app.models.document import Document as Document
from app.models.flashcard import Flashcard as Flashcard
from app.models.flashcard import FlashcardSource as FlashcardSource
from app.models.note import Note as Note
from app.models.practice_test import PracticeTest as PracticeTest
from app.models.practice_test import TestQuestion as TestQuestion
from app.models.review_log import ReviewLog as ReviewLog
from app.models.summary import DifficultyLevel as DifficultyLevel
from app.models.summary import Summary as Summary
from app.models.user import User as User