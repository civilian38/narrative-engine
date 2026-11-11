from narrative_engine.domain.database import Database
from narrative_engine.domain.models import NarrativeTemplate
from narrative_engine.domain.schemas import NarrativeTemplateCreate, NarrativeTemplateRetrieve, NarrativeTemplateUpdate
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