from sqlalchemy import select
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import SessionCharacter, SessionNarrative, StoryDialogue
from narrative_engine.domain.schemas.session_character import (
    SessionCharacterCreate,
    SessionCharacterRetrieve, SessionCharacterList, SessionCharacterUpdate,
)
from narrative_engine.exceptions import ResourceNotFoundError, InvalidOperationError


class SessionCharacterService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        session_narrative_id: int,
        name: str,
        background_description: str,
        status: str
    ) -> SessionCharacterRetrieve:
        data = SessionCharacterCreate(
            session_narrative_id=session_narrative_id,
            name=name,
            background_description=background_description,
            status=status
        )

        character = SessionCharacter(**data.model_dump())

        with self.database.session() as session:
            if session.get(SessionNarrative, session_narrative_id) is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )
            session.add(character)
            session.flush()

            result = SessionCharacterRetrieve.model_validate(
                character
            )

        return result

    def get(self, id: int) -> SessionCharacterRetrieve:
        with self.database.session() as session:
            character = session.get(
                SessionCharacter,
                id,
                options=[
                    selectinload(SessionCharacter.opinions_to_others),
                    selectinload(SessionCharacter.opinions_from_others)
                ],
            )

            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=id
                )

            return SessionCharacterRetrieve.model_validate(
                character
            )

    def list(
        self,
        search_term: str | None = None,
        session_narrative_id: int | None = None
    ) -> list[SessionCharacterList]:

        statement = select(SessionCharacter)
        if session_narrative_id is not None:
            statement = statement.where(
                SessionCharacter.session_narrative_id == session_narrative_id
            )

        if search_term and search_term.strip():
            statement = statement.where(
                SessionCharacter.name.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(SessionCharacter.id)

        with self.database.session() as session:
            characters = session.scalars(statement).all()

            return [
                SessionCharacterList.model_validate(character)
                for character in characters
            ]

    def update(
        self,
        id: int,
        **kwargs
    ) -> SessionCharacterRetrieve:

        data = SessionCharacterUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            character = session.get(
                SessionCharacter,
                id,
                options=[
                    selectinload(SessionCharacter.opinions_to_others),
                    selectinload(SessionCharacter.opinions_from_others)
                ],
            )

            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=id
                )

            for field, value in update_data.items():
                setattr(character, field, value)

            session.flush()

            return SessionCharacterRetrieve.model_validate(
                character
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            character = session.get(SessionCharacter, id)

            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=id
                )

            # Reject before scheduling any deletion; preserve all story history.
            # The deferred FK remains the database-level integrity safeguard.
            referenced = session.scalar(
                select(StoryDialogue.id)
                .where(StoryDialogue.speaker_id == id)
                .limit(1)
            )
            if referenced is not None:
                raise InvalidOperationError(
                    f"SessionCharacter with id={id} is referenced by StoryDialogue"
                )
            session.delete(character)
