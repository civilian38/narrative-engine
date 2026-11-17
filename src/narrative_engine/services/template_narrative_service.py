from sqlalchemy import select
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import TemplateNarrative
from narrative_engine.domain.schemas.template_narrative import (
    TemplateNarrativeCreate,
    TemplateNarrativeRetrieve,
    TemplateNarrativeUpdate,
    TemplateNarrativeList,
)
from narrative_engine.exceptions import ResourceNotFoundError


class TemplateNarrativeService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        name: str,
        world_description: str,
        initial_situation: str,
        template_description: str | None = None,
    ) -> TemplateNarrativeRetrieve:

        data = TemplateNarrativeCreate(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description,
        )

        template = TemplateNarrative(**data.model_dump())

        with self.database.session() as session:
            session.add(template)
            session.flush()

            result = TemplateNarrativeRetrieve.model_validate(
                template
            )

        return result

    def get(self, id: int) -> TemplateNarrativeRetrieve:
        with self.database.session() as session:
            template = session.get(
                TemplateNarrative,
                id,
                options=[
                    selectinload(TemplateNarrative.template_characters),
                    selectinload(TemplateNarrative.session_narratives)
                ],
            )

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateNarrative",
                    resource_id=id,
                )

            return TemplateNarrativeRetrieve.model_validate(
                template
            )

    def list(
        self,
        search_term: str | None = None,
    ) -> list[TemplateNarrativeList]:

        statement = select(TemplateNarrative)

        if search_term and search_term.strip():
            statement = statement.where(
                TemplateNarrative.name.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(TemplateNarrative.id)

        with self.database.session() as session:
            templates = session.scalars(statement).all()

            return [
                TemplateNarrativeList.model_validate(template)
                for template in templates
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> TemplateNarrativeRetrieve:

        data = TemplateNarrativeUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            template = session.get(
                TemplateNarrative,
                id,
                options=[
                    selectinload(TemplateNarrative.template_characters),
                    selectinload(TemplateNarrative.session_narratives)
                ],
            )

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateNarrative",
                    resource_id=id,
                )

            for field, value in update_data.items():
                setattr(template, field, value)

            session.flush()

            return TemplateNarrativeRetrieve.model_validate(
                template
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            template = session.get(TemplateNarrative, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateNarrative",
                    resource_id=id,
                )

            session.delete(template)