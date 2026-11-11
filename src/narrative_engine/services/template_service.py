from sqlalchemy import select

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import NarrativeTemplate
from narrative_engine.domain.schemas import (
    NarrativeTemplateCreate,
    NarrativeTemplateRetrieve,
    NarrativeTemplateUpdate,
    NarrativeTemplateList,
)
from narrative_engine.exceptions import ResourceNotFoundError


class TemplateService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        name: str,
        world_description: str,
        initial_situation: str,
        template_description: str | None = None,
    ) -> NarrativeTemplateRetrieve:

        data = NarrativeTemplateCreate(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description,
        )

        template = NarrativeTemplate(**data.model_dump())

        with self.database.session() as session:
            session.add(template)
            session.flush()

            result = NarrativeTemplateRetrieve.model_validate(
                template
            )

        return result

    def get(self, id: int) -> NarrativeTemplateRetrieve:
        with self.database.session() as session:
            template = session.get(NarrativeTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=id,
                )

            return NarrativeTemplateRetrieve.model_validate(
                template
            )

    def list(
        self,
        search_term: str | None = None,
    ) -> list[NarrativeTemplateList]:

        statement = select(NarrativeTemplate)

        if search_term and search_term.strip():
            statement = statement.where(
                NarrativeTemplate.name.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(NarrativeTemplate.id)

        with self.database.session() as session:
            templates = session.scalars(statement).all()

            return [
                NarrativeTemplateList.model_validate(template)
                for template in templates
            ]

    def update(
        self,
        id: int,
        **kwargs,
    ) -> NarrativeTemplateRetrieve:

        data = NarrativeTemplateUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            template = session.get(NarrativeTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=id,
                )

            for field, value in update_data.items():
                setattr(template, field, value)

            session.flush()

            return NarrativeTemplateRetrieve.model_validate(
                template
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            template = session.get(NarrativeTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=id,
                )

            session.delete(template)