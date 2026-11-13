from sqlalchemy import select
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import NarrativeTemplate, SessionNarrative, SessionCharacter
from narrative_engine.domain.schemas.session_narrative import SessionNarrativeRetrieve, SessionNarrativeList, \
    SessionNarrativeUpdate, SessionNarrativeCreate
from narrative_engine.exceptions import ResourceNotFoundError


class SessionNarrativeService:
    def __init__(self, database: Database):
        self.database = database

    def create(
            self,
            narrative_template_id: int,
            title: str | None = None,
    ) -> SessionNarrativeRetrieve:

        with self.database.session() as session:
            template = session.get(
                NarrativeTemplate,
                narrative_template_id,
                options=[
                    selectinload(
                        NarrativeTemplate.character_templates
                    )
                ],
            )

            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=narrative_template_id,
                )

            data = SessionNarrativeCreate(
                narrative_template_id=narrative_template_id,
                title=title if title is not None else template.name,
                world_description=template.world_description,
                situation=template.initial_situation,
            )

            session_narrative = SessionNarrative(
                **data.model_dump(),
                session_characters=[
                    SessionCharacter(
                        name=character.name,
                        background_description=character.background_description,
                        status=character.initial_status,
                    )
                    for character in template.character_templates
                ],
            )

            session.add(session_narrative)
            session.flush()

            result = SessionNarrativeRetrieve.model_validate(
                session_narrative
            )

        return result

    def get(self, id: int) -> SessionNarrativeRetrieve:
        with self.database.session() as session:
            session_narrative = session.get(
                SessionNarrative,
                id,
                options=[
                    selectinload(SessionNarrative.session_characters)
                ]
            )

            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=id
                )

            return SessionNarrativeRetrieve.model_validate(
                session_narrative
            )

    def list(
        self,
        search_term: str | None = None,
    ) -> list[SessionNarrativeList]:

        statement = select(SessionNarrative)

        if search_term and search_term.strip():
            statement = statement.where(
                SessionNarrative.title.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(SessionNarrative.id)

        with self.database.session() as session:
            session_narratives = session.scalars(statement).all()

            return [
                SessionNarrativeList.model_validate(session_narrative)
                for session_narrative in session_narratives
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> SessionNarrativeRetrieve:

        data = SessionNarrativeUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            session_narrative = session.get(
                SessionNarrative,
                id,
                options=[
                    selectinload(SessionNarrative.session_characters)
                ]
            )

            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=id
                )

            for field, value in update_data.items():
                setattr(session_narrative, field, value)

            session.flush()

            return SessionNarrativeRetrieve.model_validate(session_narrative)

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            session_narrative = session.get(SessionNarrative, id)

            if session_narrative is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=id
                )

            session.delete(session_narrative)