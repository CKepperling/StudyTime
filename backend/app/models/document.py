from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ForeignKey("users.id") points at the TABLE name + column, not the class.
    # This is what actually links a document to its owner in the database.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    filename: Mapped[str] = mapped_column(String(255))

    # status tracks upload -> extraction -> AI generation progress.
    # Plain string for now; could become an Enum later like difficulty_level.
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Optional[str] (not str | None) - the | union syntax needs Python 3.10+,
    # and SQLAlchemy has to actually evaluate this at runtime, so the
    # __future__ import trick doesn't save us here like it did for other cases.
    extracted_text: Mapped[Optional[str]] = mapped_column(String)

    # The other half of the relationship declared on User.
    # back_populates="documents" must match the attribute name on User exactly.
    user: Mapped["User"] = relationship(back_populates="documents")

    # Every one of these mirrors a relationship declared on the OTHER model,
    # pointing back here. back_populates on each side must name the attribute
    # on the opposite class exactly, or SQLAlchemy errors at app startup.
    summaries: Mapped[list["Summary"]] = relationship(back_populates="document")
    flashcards: Mapped[list["Flashcard"]] = relationship(back_populates="document")
    notes: Mapped[list["Note"]] = relationship(back_populates="document")
    practice_tests: Mapped[list["PracticeTest"]] = relationship(back_populates="document")