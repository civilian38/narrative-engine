from narrative_engine.domain.database import Database
from narrative_engine.services.narrative_template_service import NarrativeTemplateService


class NarrativeEngine:
    def __init__(self, db_path: str = "narrative.db"):
        self.database = Database(db_path)
        self.narrative_template_service = NarrativeTemplateService(self.database)

    def initialize(self):
        self.database.migrate()

    def close(self):
        self.database.close()

    def create_narrative_template(
        self,
        name: str,
        world_description: str,
        initial_situation: str,
        template_description: str | None = None,
    ):
        return self.narrative_template_service.create(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description,
        )

    def get_narrative_template(self, id: int):
        return self.narrative_template_service.get(id)

    def get_list_narrative_templates(self, search_term=None):
        return self.narrative_template_service.list(search_term)

    def update_narrative_template(self, id: int, **kwargs):
        return self.narrative_template_service.update(id, **kwargs)

    def delete_narrative_template(self, id: int):
        return self.narrative_template_service.delete(id)