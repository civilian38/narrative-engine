
from sqlalchemy import select
from sqlalchemy.orm import Session

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    DialogueType,
    SessionCharacter,
    StoryDialogue,
    StoryTurn,
)
from narrative_engine.domain.schemas.story_dialogue import (
    StoryDialogueCreate,
    StoryDialogueRetrieve,
    StoryDialogueList,
    StoryDialogueUpdate,
)
from narrative_engine.exceptions import (
    ResourceNotFoundError,
    InvalidOperationError,
)


class StoryDialogueService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _validate_speaker(
        session: Session,
        story_turn: StoryTurn,
        speaker_id: int | None,
    ) -> None:
        if speaker_id is None:
            return

        speaker = session.get(SessionCharacter, speaker_id)

        if speaker is None:
            raise ResourceNotFoundError(
                resource="SessionCharacter",
                resource_id=speaker_id,
            )

        if (
            speaker.session_narrative_id
            != story_turn.session_narrative_id
        ):
            raise InvalidOperationError(
                "Dialogue speaker must belong to the same "
                "SessionNarrative as its StoryTurn"
            )

    def create(
        self,
        story_turn_id: int,
        content: str,
        position: int,
        kind: DialogueType,
        speaker_id: int | None = None,
    ) -> StoryDialogueRetrieve:

        data = StoryDialogueCreate(
            story_turn_id=story_turn_id,
            content=content,
            position=position,
            kind=kind,
            speaker_id=speaker_id,
        )

        with self.database.session() as session:
            story_turn = session.get(StoryTurn, story_turn_id)

            if story_turn is None:
                raise ResourceNotFoundError(
                    resource="StoryTurn",
                    resource_id=story_turn_id,
                )

            self._validate_speaker(
                session,
                story_turn,
                data.speaker_id,
            )

            dialogue = StoryDialogue(**data.model_dump())

            session.add(dialogue)
            session.flush()

            result = StoryDialogueRetrieve.model_validate(
                dialogue
            )

        return result

    def get(self, id: int) -> StoryDialogueRetrieve:
        with self.database.session() as session:
            dialogue = session.get(StoryDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="StoryDialogue",
                    resource_id=id,
                )

            return StoryDialogueRetrieve.model_validate(
                dialogue
            )

    def list_for_story_turn(
        self,
        story_turn_id: int,
        search_term: str | None = None,
    ) -> list[StoryDialogueList]:

        statement = select(StoryDialogue).where(
            StoryDialogue.story_turn_id == story_turn_id
        )

        if search_term and search_term.strip():
            statement = statement.where(
                StoryDialogue.content.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            StoryDialogue.position,
            StoryDialogue.id,
        )

        with self.database.session() as session:
            dialogues = session.scalars(statement).all()

            return [
                StoryDialogueList.model_validate(dialogue)
                for dialogue in dialogues
            ]

    def list_for_session_narrative(
        self,
        session_narrative_id: int,
        search_term: str | None = None,
    ) -> list[StoryDialogueList]:

        statement = (
            select(StoryDialogue)
            .join(
                StoryTurn,
                StoryDialogue.story_turn_id == StoryTurn.id,
            )
            .where(
                StoryTurn.session_narrative_id
                == session_narrative_id
            )
        )

        if search_term and search_term.strip():
            statement = statement.where(
                StoryDialogue.content.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            StoryTurn.turn_index,
            StoryDialogue.position,
            StoryDialogue.id,
        )

        with self.database.session() as session:
            dialogues = session.scalars(statement).all()

            return [
                StoryDialogueList.model_validate(dialogue)
                for dialogue in dialogues
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> StoryDialogueRetrieve:

        data = StoryDialogueUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            dialogue = session.get(StoryDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="StoryDialogue",
                    resource_id=id,
                )

            # Validate the complete resulting state, not just
            # the fields supplied in this partial update.
            validated = StoryDialogueCreate(
                story_turn_id=dialogue.story_turn_id,
                content=update_data.get(
                    "content", dialogue.content
                ),
                position=update_data.get(
                    "position", dialogue.position
                ),
                kind=update_data.get(
                    "kind", dialogue.kind
                ),
                speaker_id=update_data.get(
                    "speaker_id", dialogue.speaker_id
                ),
            )

            story_turn = session.get(
                StoryTurn,
                dialogue.story_turn_id,
            )

            if story_turn is None:
                raise ResourceNotFoundError(
                    resource="StoryTurn",
                    resource_id=dialogue.story_turn_id,
                )

            self._validate_speaker(
                session,
                story_turn,
                validated.speaker_id,
            )

            for field, value in update_data.items():
                setattr(dialogue, field, value)

            session.flush()

            return StoryDialogueRetrieve.model_validate(
                dialogue
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            dialogue = session.get(StoryDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="StoryDialogue",
                    resource_id=id,
                )

            session.delete(dialogue)
