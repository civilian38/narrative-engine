from sqlalchemy import select

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import TemplateCharacter
from narrative_engine.domain.schemas.template_character import (
    TemplateCharacterCreate,
    TemplateCharacterRetrieve, TemplateCharacterList, TemplateCharacterUpdate,
)
from narrative_engine.exceptions import ResourceNotFoundError


class TemplateCharacterService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        template_narrative_id: int,
        name: str,
        background_description: str,
        initial_status: str
    ) -> TemplateCharacterRetrieve:
        data = TemplateCharacterCreate(
            template_narrative_id=template_narrative_id,
            name=name,
            background_description=background_description,
            initial_status=initial_status
        )

        template = TemplateCharacter(**data.model_dump())

        with self.database.session() as session:
            session.add(template)
            session.flush()

            result = TemplateCharacterRetrieve.model_validate(
                template
            )

        return result

    def get(self, id: int) -> TemplateCharacterRetrieve:
        with self.database.session() as session:
            template = session.get(TemplateCharacter, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateCharacter",
                    resource_id=id
                )

            return TemplateCharacterRetrieve.model_validate(
                template
            )

    def list(
        self,
        search_term: str | None = None
    ) -> list[TemplateCharacterList]:

        statement = select(TemplateCharacter)

        if search_term and search_term.strip():
            statement = statement.where(
                TemplateCharacter.name.contains(
                    search_term.strip()
                )
            )

        statement = statement.order_by(TemplateCharacter.id)

        with self.database.session() as session:
            templates = session.scalars(statement).all()

            return [
                TemplateCharacterList.model_validate(template)
                for template in templates
            ]

    def update(
        self,
        id: int,
        **kwargs
    ) -> TemplateCharacterRetrieve:

        data = TemplateCharacterUpdate(**kwargs)
        update_data = data.model_dump(exclude_unset=True)

        with self.database.session() as session:
            template = session.get(TemplateCharacter, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateCharacter",
                    resource_id=id
                )

            for field, value in update_data.items():
                setattr(template, field, value)

            session.flush()

            return TemplateCharacterRetrieve.model_validate(
                template
            )

    def delete(self, id: int) -> None:
        with self.database.session() as session:
            template = session.get(TemplateCharacter, id)

            if template is None:
                raise ResourceNotFoundError(
                    resource="TemplateCharacter",
                    resource_id=id
                )

            session.delete(template)