from datetime import datetime, timezone
from typing import List
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, Integer
from sqlalchemy import Enum as SQLEnum
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

    session_narratives: Mapped[List["SessionNarrative"]] = relationship(
        back_populates="narrative_template",
        passive_deletes=True,
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

    narrative_template_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "narrative_template.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    narrative_template: Mapped["NarrativeTemplate | None"] = relationship(
        back_populates="session_narratives",
    )

    session_characters: Mapped[List["SessionCharacter"]] = relationship(
        back_populates="session_narrative",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    story_turns: Mapped[List["StoryTurn"]] = relationship(
        back_populates="session_narrative",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StoryTurn.turn_index"
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

    # Deletion policy:
    # - A SessionCharacter must not be deleted while referenced by StoryDialogue.
    # - The database enforces this restriction through a deferred foreign key.
    # - Do not automatically delete dialogues or set their speaker_id to NULL.
    # - To remove a character referenced by existing dialogues, either remove
    #   the referencing story content explicitly or use a soft-delete strategy.
    # - Deleting the entire SessionNarrative is allowed and should cascade
    #   to its characters, turns, and dialogues.
    dialogues: Mapped[List["StoryDialogue"]] = relationship(
        back_populates="speaker",
        passive_deletes="all",
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


class StoryTurn(Base):
    __tablename__ = "story_turn"

    __table_args__ = (
        UniqueConstraint(
            "session_narrative_id",
            "turn_index",
            name="uq_story_turn_index",
        ),
        CheckConstraint(
            "turn_index >= 0",
            name="ck_story_turn_index",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    user_input: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    session_narrative_id: Mapped[int] = mapped_column(
        ForeignKey('session_narrative.id', ondelete='CASCADE'),
        nullable=False
    )

    session_narrative: Mapped["SessionNarrative"] = relationship(
        back_populates="story_turns",
    )

    story_dialogues: Mapped[List["StoryDialogue"]] = relationship(
        back_populates="story_turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StoryDialogue.position"
    )


class DialogueType(str, Enum):
    Dialogue = "Dialogue"
    Narration = "Narration"


class StoryDialogue(Base):
    __tablename__ = "story_dialogue"

    __table_args__ = (
        UniqueConstraint(
            "story_turn_id",
            "position",
            name="uq_story_dialogue_position",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_story_dialogue_position",
        ),
        CheckConstraint(
            """
            (kind = 'Dialogue' AND speaker_id IS NOT NULL)
            OR
            (kind = 'Narration' AND speaker_id IS NULL)
            """,
            name="ck_story_dialogue_speaker",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    kind: Mapped[DialogueType] = mapped_column(
        SQLEnum(DialogueType, validate_strings=True),
        nullable=False
    )

    # Use a deferred NO ACTION foreign key instead of RESTRICT.
    #
    # This allows SQLite to evaluate referential integrity at transaction commit,
    # after cascading deletions have completed.
    #
    # Expected behavior:
    # - Deleting a character referenced by a dialogue must fail.
    # - Deleting a character with no referencing dialogues must succeed.
    # - Deleting an entire narrative session must remove its dialogues
    #   and characters through ON DELETE CASCADE.
    #
    # Foreign key enforcement must be enabled with PRAGMA foreign_keys=ON.
    speaker_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "session_character.id",
            ondelete="NO ACTION",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )

    speaker: Mapped["SessionCharacter | None"] = relationship(
        back_populates="dialogues",
    )

    story_turn_id: Mapped[int] = mapped_column(
        ForeignKey('story_turn.id', ondelete='CASCADE'),
        nullable=False
    )

    story_turn: Mapped["StoryTurn"] = relationship(
        back_populates="story_dialogues",
    )