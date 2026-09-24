from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.document import Document


class PracticeTest(Base):
    __tablename__ = "practice_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="practice_tests")
    # One PracticeTest has many TestQuestions - this is the "many" side.
    # No TYPE_CHECKING import needed for "TestQuestion" since it's defined
    # further down in this SAME file, so it's already in module scope.
    # cascade="all, delete-orphan": a question has no meaning without its
    # test, same reasoning as Document's children and Flashcard's review_logs.
    questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="practice_test", cascade="all, delete-orphan"
    )


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Table name here is "practice_tests" (matches PracticeTest.__tablename__),
    # NOT "practice_test" singular - same mistake to watch for as summary.py earlier.
    practice_test_id: Mapped[int] = mapped_column(ForeignKey("practice_tests.id"))

    question: Mapped[str] = mapped_column(String)
    correct_answer: Mapped[str] = mapped_column(String)

    practice_test: Mapped["PracticeTest"] = relationship(back_populates="questions")