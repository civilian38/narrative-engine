from typing import List
from sqlalchemy import select

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import NarrativeTemplate
from narrative_engine.domain.schemas import NarrativeTemplateCreate, NarrativeTemplateRetrieve, NarrativeTemplateUpdate, NarrativeTemplateList
from narrative_engine.exceptions import ResourceNotFoundError


class NarrativeEngine:
    def __init__(
        self,
        db_path: str = "narrative.db",
    ):
        self.database = Database(db_path)

    def initialize(self):
        self.database.migrate()

    def close(self):
        self.database.close()

    '''
    Narrative Template Handling
    '''

    def create_narrative_template(self,
                                  name: str,
                                  world_description: str,
                                  initial_situation: str,
                                  template_description: str | None = None) ->NarrativeTemplateRetrieve:
        data = NarrativeTemplateCreate(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description
        )

        db_template = NarrativeTemplate(
            **data.model_dump(exclude_none=True)
        )

        with self.database.session() as session:
            session.add(db_template)
            session.flush()

            result = NarrativeTemplateRetrieve.model_validate(
                db_template
            )

        return result

    def get_list_narrative_templates(self, search_term: str | None = None) -> List[NarrativeTemplateList]:

        statement = select(NarrativeTemplate)

        if search_term and search_term.strip():
            statement = statement.where(
                NarrativeTemplate.name.contains(search_term)
            )

        with self.database.session() as session:
            templates = session.scalars(statement).all()
            result = [NarrativeTemplateList.model_validate(template) for template in templates]
            return result

    def get_narrative_template(self, id: int) -> NarrativeTemplateRetrieve:
        with self.database.session() as session:
            template = session.get(NarrativeTemplate, id)
            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=id,
                )

            result = NarrativeTemplateRetrieve.model_validate(template)
            return result

    def update_narrative_template(
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

            result = NarrativeTemplateRetrieve.model_validate(
                template
            )

        return result

    def delete_narrative_template(self, id: int) -> None:
        with self.database.session() as session:
            template = session.get(NarrativeTemplate, id)
            if template is None:
                raise ResourceNotFoundError(
                    resource="NarrativeTemplate",
                    resource_id=id,
                )
            session.delete(template)
            session.flush()