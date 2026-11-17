from sqlalchemy import select, or_

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    SessionNarrative,
    SessionCharacter,
    SessionCharacterOpinion,
)
from narrative_engine.domain.schemas.session_character_opinion import (
    SessionCharacterOpinionCreate,
    SessionCharacterOpinionRetrieve,
    SessionCharacterOpinionList,
    SessionCharacterOpinionUpdate,
)
from narrative_engine.exceptions import (
    ResourceNotFoundError,
    InvalidOperationError,
)


class SessionCharacterOpinionService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _validate_characters(
        session,
        session_narrative_id: int,
        from_character_id: int,
        to_character_id: int,
    ) -> None:

        if from_character_id == to_character_id:
            raise InvalidOperationError(
                "A character cannot have an opinion about themselves"
            )

        characters = session.scalars(
            select(SessionCharacter).where(
                SessionCharacter.id.in_([
                    from_character_id,
                    to_character_id,
                ])
            )
        ).all()

        characters_by_id = {
            character.id: character
            for character in characters
        }

        for character_id in (
            from_character_id,
            to_character_id,
        ):
            character = characters_by_id.get(character_id)

            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=character_id,
                )

            if (
                character.session_narrative_id
                != session_narrative_id
            ):
                raise InvalidOperationError(
                    "Both characters must belong to the same "
                    "SessionNarrative"
                )

    def create(
        self,
        session_narrative_id: int,
        from_character_id: int,
        to_character_id: int,
        opinion: str,
    ) -> SessionCharacterOpinionRetrieve:

        data = SessionCharacterOpinionCreate(
            session_narrative_id=session_narrative_id,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            opinion=opinion,
        )

        with self.database.session() as session:

            session_narrative = session.get(
                SessionNarrative,
                data.session_narrative_id,
            )

            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )

            self._validate_characters(
                session=session,
                session_narrative_id=data.session_narrative_id,
                from_character_id=data.from_character_id,
                to_character_id=data.to_character_id,
            )

            # One opinion per directed character pair.
            existing = session.scalar(
                select(SessionCharacterOpinion).where(
                    SessionCharacterOpinion.from_character_id
                    == data.from_character_id,
                    SessionCharacterOpinion.to_character_id
                    == data.to_character_id,
                )
            )

            if existing is not None:
                raise InvalidOperationError(
                    "An opinion already exists for this character pair"
                )

            opinion_record = SessionCharacterOpinion(
                **data.model_dump()
            )

            session.add(opinion_record)
            session.flush()

            result = SessionCharacterOpinionRetrieve.model_validate(
                opinion_record
            )

        return result

    def get(self, id: int) -> SessionCharacterOpinionRetrieve:

        with self.database.session() as session:

            opinion = session.get(
                SessionCharacterOpinion,
                id,
            )

            if opinion is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterOpinion",
                    resource_id=id,
                )

            return SessionCharacterOpinionRetrieve.model_validate(
                opinion
            )

    def list(
        self,
        session_narrative_id: int,
        character_id: int | None = None,
    ) -> list[SessionCharacterOpinionList]:

        with self.database.session() as session:

            # Validate the session.
            session_narrative = session.get(
                SessionNarrative,
                session_narrative_id,
            )

            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )

            statement = select(
                SessionCharacterOpinion
            ).where(
                SessionCharacterOpinion.session_narrative_id
                == session_narrative_id
            )

            # Optional character-specific filtering.
            if character_id is not None:

                character = session.get(
                    SessionCharacter,
                    character_id,
                )

                if character is None:
                    raise ResourceNotFoundError(
                        resource="SessionCharacter",
                        resource_id=character_id,
                    )

                if (
                    character.session_narrative_id
                    != session_narrative_id
                ):
                    raise InvalidOperationError(
                        "Character must belong to the specified "
                        "SessionNarrative"
                    )

                statement = statement.where(
                    or_(
                        SessionCharacterOpinion.from_character_id
                        == character_id,
                        SessionCharacterOpinion.to_character_id
                        == character_id,
                    )
                )

            statement = statement.order_by(
                SessionCharacterOpinion.id
            )

            opinions = session.scalars(statement).all()

            return [
                SessionCharacterOpinionList.model_validate(opinion)
                for opinion in opinions
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> SessionCharacterOpinionRetrieve:

        data = SessionCharacterOpinionUpdate(**kwargs)

        update_data = data.model_dump(
            exclude_unset=True
        )

        with self.database.session() as session:

            opinion = session.get(
                SessionCharacterOpinion,
                id,
            )

            if opinion is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterOpinion",
                    resource_id=id,
                )

            for field, value in update_data.items():
                setattr(opinion, field, value)

            session.flush()

            return SessionCharacterOpinionRetrieve.model_validate(
                opinion
            )

    def delete(self, id: int) -> None:

        with self.database.session() as session:

            opinion = session.get(
                SessionCharacterOpinion,
                id,
            )

            if opinion is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacterOpinion",
                    resource_id=id,
                )

            session.delete(opinion)