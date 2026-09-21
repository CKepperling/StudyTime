from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# TYPE_CHECKING is False at runtime, so this import never actually runs
# (avoiding a circular import with document.py) - it only exists so
# ruff and your editor can resolve the "Document" string below.
if TYPE_CHECKING:
    from app.models.document import Document


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True enforces at the DB level that no two users share an email
    email: Mapped[str] = mapped_column(String(255), unique=True)

    # hashed_password, never the raw password — hashing itself comes in T6 (auth)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # "Document" is in quotes because Document is defined in a different file
    # and hasn't been imported yet at the point Python reads this class.
    # list[...] means one User can have many Documents.
    documents: Mapped[list["Document"]] = relationship(back_populates="user")