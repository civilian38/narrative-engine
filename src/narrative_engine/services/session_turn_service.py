from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    SessionDialogue,
    SessionNarrative,
    SessionTurn,
)
from narrative_engine.domain.schemas.session_turn import (
    SessionTurnCreate,
    SessionTurnRetrieve,
    SessionTurnList,
    SessionTurnUpdate,
)
from narrative_engine.exceptions import ResourceNotFoundError

class SessionTurnService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        session_narrative_id: int,
        user_input: str,
        session_dialogues: list[SessionDialogue]
    ) -> SessionTurnRetrieve:

        with self.database.session() as session:
            session_narrative = session.get(SessionNarrative, session_narrative_id)
            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )

            next_turn_index = session.scalar(
                select(func.max(SessionTurn.turn_index))
                .where(
                    SessionTurn.session_narrative_id == session_narrative_id
                )
            )

            next_turn_index = (
                next_turn_index + 1
                if next_turn_index is not None
                else 0
            )

            data = SessionTurnCreate(
                turn_index=next_turn_index,
                user_input=user_input,
                session_narrative_id=session_narrative_id,
            )

            session_turn = SessionTurn(
                **data.model_dump(),
                session_dialogues=session_dialogues
            )

            session.add(session_turn)
            session.flush()

            result = SessionTurnRetrieve.model_validate(
                session_turn
            )

        return result

    def get(self, id: int) -> SessionTurnRetrieve:
        with self.database.session() as session:
            session_turn = session.get(
                SessionTurn,
                id,
                options=[
                    selectinload(SessionTurn.session_dialogues)
                ],
            )

            if session_turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=id,
                )

            return SessionTurnRetrieve.model_validate(
                session_turn
            )

    def list(
            self,
            search_term: str | None = None,
            session_narrative_id: int | None = None,
    ) -> list[SessionTurnList]:

        statement = select(SessionTurn)

        if session_narrative_id is not None:
            statement = statement.where(
                SessionTurn.session_narrative_id == session_narrative_id
            )

        if search_term and search_term.strip():
            statement = statement.where(
                SessionTurn.user_input.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            SessionTurn.session_narrative_id,
            SessionTurn.turn_index,
        )

        with self.database.session() as session:
            session_turns = session.scalars(statement).all()

            return [
                SessionTurnList.model_validate(session_turn)
                for session_turn in session_turns
            ]

    def update(
            self,
            id: int,
            **kwargs,
    ) -> SessionTurnRetrieve:

        data = SessionTurnUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            session_turn = session.get(
                SessionTurn,
                id,
                options=[
                    selectinload(SessionTurn.session_dialogues)
                ],
            )

            if session_turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=id,
                )

            for field, value in update_data.items():
                setattr(session_turn, field, value)

            session.flush()

            return SessionTurnRetrieve.model_validate(
                session_turn
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            session_turn = session.get(SessionTurn, id)

            if session_turn is None:
                raise ResourceNotFoundError(
                    resource="SessionTurn",
                    resource_id=id,
                )

            session.delete(session_turn)
