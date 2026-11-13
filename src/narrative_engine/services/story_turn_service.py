from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    StoryDialogue,
    SessionNarrative,
    StoryTurn,
)
from narrative_engine.domain.schemas.story_turn import (
    StoryTurnCreate,
    StoryTurnRetrieve,
    StoryTurnList,
    StoryTurnUpdate,
)
from narrative_engine.exceptions import ResourceNotFoundError

class StoryTurnService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        session_narrative_id: int,
        user_input: str,
        story_dialogues: list[StoryDialogue]
    ) -> StoryTurnRetrieve:

        with self.database.session() as session:
            session_narrative = session.get(SessionNarrative, session_narrative_id)
            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )

            next_turn_index = session.scalar(
                select(func.max(StoryTurn.turn_index))
                .where(
                    StoryTurn.session_narrative_id == session_narrative_id
                )
            )

            next_turn_index = (
                next_turn_index + 1
                if next_turn_index is not None
                else 0
            )

            data = StoryTurnCreate(
                turn_index=next_turn_index,
                user_input=user_input,
                session_narrative_id=session_narrative_id,
            )

            story_turn = StoryTurn(
                **data.model_dump(),
                story_dialogues=story_dialogues
            )

            session.add(story_turn)
            session.flush()

            result = StoryTurnRetrieve.model_validate(
                story_turn
            )

        return result

    def get(self, id: int) -> StoryTurnRetrieve:
        with self.database.session() as session:
            story_turn = session.get(
                StoryTurn,
                id,
                options=[
                    selectinload(StoryTurn.story_dialogues)
                ],
            )

            if story_turn is None:
                raise ResourceNotFoundError(
                    resource="StoryTurn",
                    resource_id=id,
                )

            return StoryTurnRetrieve.model_validate(
                story_turn
            )

    def list(
            self,
            search_term: str | None = None,
            session_narrative_id: int | None = None,
    ) -> list[StoryTurnList]:

        statement = select(StoryTurn)

        if session_narrative_id is not None:
            statement = statement.where(
                StoryTurn.session_narrative_id == session_narrative_id
            )

        if search_term and search_term.strip():
            statement = statement.where(
                StoryTurn.user_input.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(
            StoryTurn.session_narrative_id,
            StoryTurn.turn_index,
        )

        with self.database.session() as session:
            story_turns = session.scalars(statement).all()

            return [
                StoryTurnList.model_validate(story_turn)
                for story_turn in story_turns
            ]

    def update(
            self,
            id: int,
            **kwargs,
    ) -> StoryTurnRetrieve:

        data = StoryTurnUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            story_turn = session.get(
                StoryTurn,
                id,
                options=[
                    selectinload(StoryTurn.story_dialogues)
                ],
            )

            if story_turn is None:
                raise ResourceNotFoundError(
                    resource="StoryTurn",
                    resource_id=id,
                )

            for field, value in update_data.items():
                setattr(story_turn, field, value)

            session.flush()

            return StoryTurnRetrieve.model_validate(
                story_turn
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            story_turn = session.get(StoryTurn, id)

            if story_turn is None:
                raise ResourceNotFoundError(
                    resource="StoryTurn",
                    resource_id=id,
                )

            session.delete(story_turn)
