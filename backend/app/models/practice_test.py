from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PracticeTest(Base):
    __tablename__ = "practice_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="practice_tests")
    # One PracticeTest has many TestQuestions - this is the "many" side.
    questions: Mapped[list["TestQuestion"]] = relationship(back_populates="practice_test")


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Note the table name here is "practice_tests" (matches PracticeTest.__tablename__),
    # NOT "practice_test" singular - same mistake to watch for as in summary.py earlier.
    practice_test_id: Mapped[int] = mapped_column(ForeignKey("practice_tests.id"))

    question: Mapped[str] = mapped_column(String)
    correct_answer: Mapped[str] = mapped_column(String)

    practice_test: Mapped["PracticeTest"] = relationship(back_populates="questions")