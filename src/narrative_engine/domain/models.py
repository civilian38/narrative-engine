from typing import List

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
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

    character_templates: Mapped[List["CharacterTemplate"]] = relationship(
        back_populates="narrative_template",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class CharacterTemplate(Base):
    __tablename__ = "character_template"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    background_description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    initial_status: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    narrative_template_id: Mapped[int] = mapped_column(
        ForeignKey('narrative_template.id', ondelete='CASCADE'),
        nullable=False
    )

    narrative_template: Mapped["NarrativeTemplate"] = relationship(
        back_populates='character_templates'
    )