from typing import List

from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, CheckConstraint
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


class SessionNarrative(Base):
    __tablename__ = "session_narrative"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    world_description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    situation: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    session_characters: Mapped[List["SessionCharacter"]] = relationship(
        back_populates="session_narrative",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class SessionCharacter(Base):
    __tablename__ = "session_character"

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

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    session_narrative_id: Mapped[int] = mapped_column(
        ForeignKey('session_narrative.id', ondelete='CASCADE'),
        nullable=False
    )

    session_narrative: Mapped["SessionNarrative"] = relationship(
        back_populates='session_characters',
    )

    opinions_to_others: Mapped[List["SessionCharacterOpinion"]] = relationship(
        back_populates="from_character",
        foreign_keys="SessionCharacterOpinion.from_character_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    opinions_from_others: Mapped[List["SessionCharacterOpinion"]] = relationship(
        back_populates="to_character",
        foreign_keys="SessionCharacterOpinion.to_character_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class SessionCharacterOpinion(Base):
    __tablename__ = "session_character_opinion"

    __table_args__ = (
        UniqueConstraint(
            "from_character_id", "to_character_id", name="uq_session_character_opinion_pair"
        ),
        CheckConstraint(
            "from_character_id != to_character_id", name="ck_session_character_opinion_no_self"
        )
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    opinion: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    from_character_id: Mapped[int] = mapped_column(
        ForeignKey('session_character.id', ondelete='CASCADE'),
        nullable=False
    )

    to_character_id: Mapped[int] = mapped_column(
        ForeignKey('session_character.id', ondelete='CASCADE'),
        nullable=False
    )

    from_character: Mapped["SessionCharacter"] = relationship(
        back_populates="opinions_to_others",
        foreign_keys=[from_character_id],
    )

    to_character: Mapped["SessionCharacter"] = relationship(
        back_populates="opinions_from_others",
        foreign_keys=[to_character_id],
    )