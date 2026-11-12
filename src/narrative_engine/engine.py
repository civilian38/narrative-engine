from narrative_engine.domain.database import Database
from narrative_engine.services.narrative_template_service import NarrativeTemplateService
from narrative_engine.services.character_template_service import CharacterTemplateService
from narrative_engine.services.session_narrative_service import SessionNarrativeService


class NarrativeEngine:
    def __init__(self, db_path: str = "narrative.db"):
        self.database = Database(db_path)
        self.narrative_template_service = NarrativeTemplateService(self.database)
        self.character_template_service = CharacterTemplateService(self.database)
        self.session_narrative_service = SessionNarrativeService(self.database)

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
        self.narrative_template_service.delete(id)

    def create_character_template(
        self,
        narrative_template_id: int,
        name: str,
        background_description: str,
        initial_status: str
    ):
        return self.character_template_service.create(
            narrative_template_id=narrative_template_id,
            name=name,
            background_description=background_description,
            initial_status=initial_status,
        )

    def get_character_template(self, id: int):
        return self.character_template_service.get(id)

    def get_list_character_templates(self, search_term=None):
        return self.character_template_service.list(search_term)

    def update_character_template(self, id: int, **kwargs):
        return self.character_template_service.update(id, **kwargs)

    def delete_character_template(self, id: int):
        self.character_template_service.delete(id)

    def create_session_narrative_template(
        self,
        narrative_template_id: int,
        title: str | None = None
    ):
        return self.session_narrative_service.create(
            narrative_template_id=narrative_template_id,
            title=title
        )

    def get_session_narrative(self, id: int):
        return self.session_narrative_service.get(id)

    def get_list_session_narratives(self, search_term=None):
        return self.session_narrative_service.list(search_term)

    def update_session_narrative(self, id: int, **kwargs):
        return self.session_narrative_service.update(id, **kwargs)

    def delete_session_narrative(self, id: int):
        self.session_narrative_service.delete(id)