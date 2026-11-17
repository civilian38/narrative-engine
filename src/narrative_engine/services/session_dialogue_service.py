
from sqlalchemy import select
from sqlalchemy.orm import Session

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    DialogueType,
    SessionCharacter,
    SessionDialogue,
    SessionTurn,
)
from narrative_engine.domain.schemas.session_dialogue import (
    SessionDialogueCreate,
    SessionDialogueRetrieve,
    SessionDialogueList,
    SessionDialogueUpdate,
)
from narrative_engine.exceptions import (
    ResourceNotFoundError,
    InvalidOperationError,
)


class SessionDialogueService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _validate_speaker(
        session: Session,
        session_turn: SessionTurn,
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
            != session_turn.session_narrative_id
        ):
            raise InvalidOperationError(
                "Dialogue speaker must belong to the same "
                "SessionNarrative as its SessionTurn"
            )

    def create(
        self,
        session_turn_id: int,
        content: str,
        position: int,
        kind: DialogueType,
        speaker_id: int | None = None,
    ) -> SessionDialogueRetrieve:

        data = SessionDialogueCreate(
            session_turn_id=session_turn_id,
            content=content,
            position=position,
            kind=kind,
            speaker_id=speaker_id,
        )

        with self.database.session() as session:
            session_turn = session.get(SessionTurn, session_turn_id)

            if session_turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=session_turn_id,
                )

            self._validate_speaker(
                session,
                session_turn,
                data.speaker_id,
            )

            dialogue = SessionDialogue(**data.model_dump())

            session.add(dialogue)
            session.flush()

            result = SessionDialogueRetrieve.model_validate(
                dialogue
            )

        return result

    def get(self, id: int) -> SessionDialogueRetrieve:
        with self.database.session() as session:
            dialogue = session.get(SessionDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="SessionDialogue",
                    resource_id=id,
                )

            return SessionDialogueRetrieve.model_validate(
                dialogue
            )

    def list_for_session_turn(
        self,
        session_turn_id: int,
        search_term: str | None = None,
    ) -> list[SessionDialogueList]:

        statement = select(SessionDialogue).where(
            SessionDialogue.session_turn_id == session_turn_id
        )

        if search_term and search_term.strip():
            statement = statement.where(
                SessionDialogue.content.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            SessionDialogue.position,
            SessionDialogue.id,
        )

        with self.database.session() as session:
            dialogues = session.scalars(statement).all()

            return [
                SessionDialogueList.model_validate(dialogue)
                for dialogue in dialogues
            ]

    def list_for_session_narrative(
        self,
        session_narrative_id: int,
        search_term: str | None = None,
    ) -> list[SessionDialogueList]:

        statement = (
            select(SessionDialogue)
            .join(
                SessionTurn,
                SessionDialogue.session_turn_id == SessionTurn.id,
            )
            .where(
                SessionTurn.session_narrative_id
                == session_narrative_id
            )
        )

        if search_term and search_term.strip():
            statement = statement.where(
                SessionDialogue.content.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            SessionTurn.turn_index,
            SessionDialogue.position,
            SessionDialogue.id,
        )

        with self.database.session() as session:
            dialogues = session.scalars(statement).all()

            return [
                SessionDialogueList.model_validate(dialogue)
                for dialogue in dialogues
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> SessionDialogueRetrieve:

        data = SessionDialogueUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            dialogue = session.get(SessionDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="SessionDialogue",
                    resource_id=id,
                )

            # Validate the complete resulting state, not just
            # the fields supplied in this partial update.
            validated = SessionDialogueCreate(
                session_turn_id=dialogue.session_turn_id,
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

            session_turn = session.get(
                SessionTurn,
                dialogue.session_turn_id,
            )

            if session_turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=dialogue.session_turn_id,
                )

            self._validate_speaker(
                session,
                session_turn,
                validated.speaker_id,
            )

            for field, value in update_data.items():
                setattr(dialogue, field, value)

            session.flush()

            return SessionDialogueRetrieve.model_validate(
                dialogue
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            dialogue = session.get(SessionDialogue, id)

            if dialogue is None:
                raise ResourceNotFoundError(
                    resource="SessionDialogue",
                    resource_id=id,
                )

            session.delete(dialogue)
