from sqlalchemy import select

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    SessionCharacter,
    SessionCharacterMemory,
    SessionTurn,
)
from narrative_engine.domain.schemas.session_character_memory import (
    SessionCharacterMemoryCreate,
    SessionCharacterMemoryList,
    SessionCharacterMemoryRetrieve,
    SessionCharacterMemoryUpdate,
)
from narrative_engine.exceptions import (
    InvalidOperationError,
    ResourceNotFoundError,
)


class SessionCharacterMemoryService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        session_character_id: int,
        session_turn_id: int,
        memory: str,
    ) -> SessionCharacterMemoryRetrieve:
        data = SessionCharacterMemoryCreate(
            session_character_id=session_character_id,
            session_turn_id=session_turn_id,
            memory=memory,
        )

        with self.database.session() as session:
            character = session.get(SessionCharacter, data.session_character_id)
            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=data.session_character_id,
                )

            turn = session.get(SessionTurn, data.session_turn_id)
            if turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=data.session_turn_id,
                )

            if character.session_narrative_id != turn.session_narrative_id:
                raise InvalidOperationError(
                    "SessionCharacter and SessionTurn must belong to the same "
                    "SessionNarrative"
                )

            existing = session.scalar(
                select(SessionCharacterMemory).where(
                    SessionCharacterMemory.session_character_id
                    == data.session_character_id,
                    SessionCharacterMemory.session_turn_id == data.session_turn_id,
                )
            )
            if existing is not None:
                raise InvalidOperationError(
                    "A memory already exists for this character and turn"
                )

            memory_record = SessionCharacterMemory(**data.model_dump())
            session.add(memory_record)
            session.flush()
            return SessionCharacterMemoryRetrieve.model_validate(memory_record)

    def get(self, id: int) -> SessionCharacterMemoryRetrieve:
        with self.database.session() as session:
            memory = session.get(SessionCharacterMemory, id)
            if memory is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterMemory",
                    resource_id=id,
                )
            return SessionCharacterMemoryRetrieve.model_validate(memory)

    def list_for_character(
        self,
        session_character_id: int,
    ) -> list[SessionCharacterMemoryList]:
        with self.database.session() as session:
            character = session.get(SessionCharacter, session_character_id)
            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=session_character_id,
                )

            memories = session.scalars(
                select(SessionCharacterMemory)
                .join(SessionTurn, SessionCharacterMemory.session_turn_id == SessionTurn.id)
                .where(SessionCharacterMemory.session_character_id == session_character_id)
                .order_by(SessionTurn.turn_index, SessionTurn.id)
            ).all()
            return [
                SessionCharacterMemoryList.model_validate(memory)
                for memory in memories
            ]

    def list_for_turn(
        self,
        session_turn_id: int,
    ) -> list[SessionCharacterMemoryList]:
        with self.database.session() as session:
            turn = session.get(SessionTurn, session_turn_id)
            if turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=session_turn_id,
                )

            memories = session.scalars(
                select(SessionCharacterMemory)
                .where(SessionCharacterMemory.session_turn_id == session_turn_id)
                .order_by(
                    SessionCharacterMemory.session_character_id,
                    SessionCharacterMemory.id,
                )
            ).all()
            return [
                SessionCharacterMemoryList.model_validate(memory)
                for memory in memories
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> SessionCharacterMemoryRetrieve:
        data = SessionCharacterMemoryUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            memory = session.get(SessionCharacterMemory, id)
            if memory is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterMemory",
                    resource_id=id,
                )
            for field, value in update_data.items():
                setattr(memory, field, value)
            session.flush()
            return SessionCharacterMemoryRetrieve.model_validate(memory)

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            memory = session.get(SessionCharacterMemory, id)
            if memory is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterMemory",
                    resource_id=id,
                )
            session.delete(memory)
