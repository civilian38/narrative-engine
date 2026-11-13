from sqlalchemy import select

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import CharacterTemplate
from narrative_engine.domain.schemas.character_template import (
    CharacterTemplateCreate,
    CharacterTemplateRetrieve, CharacterTemplateList, CharacterTemplateUpdate,
)
from narrative_engine.exceptions import ResourceNotFoundError


class CharacterTemplateService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        narrative_template_id: int,
        name: str,
        background_description: str,
        initial_status: str
    ) -> CharacterTemplateRetrieve:
        data = CharacterTemplateCreate(
            narrative_template_id=narrative_template_id,
            name=name,
            background_description=background_description,
            initial_status=initial_status
        )

        template = CharacterTemplate(**data.model_dump())

        with self.database.session() as session:
            session.add(template)
            session.flush()

            result = CharacterTemplateRetrieve.model_validate(
                template
            )

        return result

    def get(self, id: int) -> CharacterTemplateRetrieve:
        with self.database.session() as session:
            template = session.get(CharacterTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="CharacterTemplate",
                    resource_id=id
                )

            return CharacterTemplateRetrieve.model_validate(
                template
            )

    def list(
        self,
        search_term: str | None = None
    ) -> list[CharacterTemplateList]:

        statement = select(CharacterTemplate)

        if search_term and search_term.strip():
            statement = statement.where(
                CharacterTemplate.name.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(CharacterTemplate.id)

        with self.database.session() as session:
            templates = session.scalars(statement).all()

            return [
                CharacterTemplateList.model_validate(template)
                for template in templates
            ]

    def update(
        self,
        id: int,
        **kwargs
    ) -> CharacterTemplateRetrieve:

        data = CharacterTemplateUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            template = session.get(CharacterTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="CharacterTemplate",
                    resource_id=id
                )

            for field, value in update_data.items():
                setattr(template, field, value)

            session.flush()

            return CharacterTemplateRetrieve.model_validate(
                template
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            template = session.get(CharacterTemplate, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="CharacterTemplate",
                    resource_id=id
                )

            session.delete(template)