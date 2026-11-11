from sqlalchemy import String, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class NarrativeTemplate(Base):
    __tablename__ = "narrative_template"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    template_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    world_description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    initial_situation: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
