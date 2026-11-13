from types import TracebackType

from narrative_engine.domain.models import StoryDialogue
from narrative_engine.domain.schemas.session_character import (
    SessionCharacterRetrieve,
    SessionCharacterList,
)
from narrative_engine.domain.schemas.story_turn import StoryTurnRetrieve, StoryTurnList
from narrative_engine.services.session_character_service import SessionCharacterService
from typing import Self

from narrative_engine.domain.database import Database
from narrative_engine.domain.schemas.narrative_template import (
    NarrativeTemplateRetrieve,
    NarrativeTemplateList,
)
from narrative_engine.domain.schemas.character_template import (
    CharacterTemplateRetrieve,
    CharacterTemplateList,
)
from narrative_engine.domain.schemas.session_narrative import (
    SessionNarrativeRetrieve,
    SessionNarrativeList,
)
from narrative_engine.services.narrative_template_service import (
    NarrativeTemplateService,
)
from narrative_engine.services.character_template_service import (
    CharacterTemplateService,
)
from narrative_engine.services.session_narrative_service import (
    SessionNarrativeService,
)
from narrative_engine.services.story_turn_service import (
    StoryTurnService
)


class NarrativeEngine:
    """Public facade for narrative engine operations."""

    def __init__(self, db_path: str = "narrative.db") -> None:
        self.database = Database(db_path)
        self.session_character_service = SessionCharacterService(
            self.database
        )
        self.narrative_template_service = NarrativeTemplateService(
            self.database
        )
        self.character_template_service = CharacterTemplateService(
            self.database
        )
        self.session_narrative_service = SessionNarrativeService(
            self.database
        )
        self.story_turn_service = StoryTurnService(
            self.database
        )

    def initialize(self) -> None:
        self.database.migrate()

    def close(self) -> None:
        self.database.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # Narrative templates

    def create_narrative_template(
        self,
        name: str,
        world_description: str,
        initial_situation: str,
        template_description: str | None = None,
    ) -> NarrativeTemplateRetrieve:
        return self.narrative_template_service.create(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description,
        )

    def get_narrative_template(
        self,
        resource_id: int,
    ) -> NarrativeTemplateRetrieve:
        return self.narrative_template_service.get(resource_id)

    def list_narrative_templates(
        self,
        search_term: str | None = None,
    ) -> list[NarrativeTemplateList]:
        return self.narrative_template_service.list(search_term)

    def update_narrative_template(
        self,
        resource_id: int,
        **kwargs,
    ) -> NarrativeTemplateRetrieve:
        return self.narrative_template_service.update(
            resource_id, **kwargs
        )

    def delete_narrative_template(
        self,
        resource_id: int,
    ) -> None:
        self.narrative_template_service.delete(resource_id)

    # Character templates

    def create_character_template(
        self,
        narrative_template_id: int,
        name: str,
        background_description: str,
        initial_status: str,
    ) -> CharacterTemplateRetrieve:
        return self.character_template_service.create(
            narrative_template_id=narrative_template_id,
            name=name,
            background_description=background_description,
            initial_status=initial_status,
        )

    def get_character_template(
        self,
        resource_id: int,
    ) -> CharacterTemplateRetrieve:
        return self.character_template_service.get(resource_id)

    def list_character_templates(
        self,
        search_term: str | None = None,
    ) -> list[CharacterTemplateList]:
        return self.character_template_service.list(search_term)

    def update_character_template(
        self,
        resource_id: int,
        **kwargs,
    ) -> CharacterTemplateRetrieve:
        return self.character_template_service.update(
            resource_id, **kwargs
        )

    def delete_character_template(
        self,
        resource_id: int,
    ) -> None:
        self.character_template_service.delete(resource_id)

    # Session narratives

    def create_session_narrative(
        self,
        narrative_template_id: int,
        title: str | None = None,
    ) -> SessionNarrativeRetrieve:
        return self.session_narrative_service.create(
            narrative_template_id=narrative_template_id,
            title=title,
        )

    def get_session_narrative(
        self,
        resource_id: int,
    ) -> SessionNarrativeRetrieve:
        return self.session_narrative_service.get(resource_id)

    def list_session_narratives(
        self,
        search_term: str | None = None,
    ) -> list[SessionNarrativeList]:
        return self.session_narrative_service.list(search_term)

    def update_session_narrative(
        self,
        resource_id: int,
        **kwargs,
    ) -> SessionNarrativeRetrieve:
        return self.session_narrative_service.update(
            resource_id, **kwargs
        )

    def delete_session_narrative(
        self,
        resource_id: int,
    ) -> None:
        self.session_narrative_service.delete(resource_id)

    # Session characters

    def create_session_character(
        self,
        session_narrative_id: int,
        name: str,
        background_description: str,
        status: str,
    ) -> SessionCharacterRetrieve:
        return self.session_character_service.create(
            session_narrative_id=session_narrative_id,
            name=name,
            background_description=background_description,
            status=status,
        )

    def get_session_character(self, resource_id: int) -> SessionCharacterRetrieve:
        return self.session_character_service.get(resource_id)

    def list_session_characters(
        self,
        search_term: str | None = None,
        session_narrative_id: int | None = None,
    ) -> list[SessionCharacterList]:
        return self.session_character_service.list(
            search_term=search_term,
            session_narrative_id=session_narrative_id,
        )

    def update_session_character(
        self, resource_id: int, **kwargs,
    ) -> SessionCharacterRetrieve:
        return self.session_character_service.update(resource_id, **kwargs)

    def delete_session_character(self, resource_id: int) -> None:
        self.session_character_service.delete(resource_id)

    # Story turns

    def create_story_turn(
            self,
            session_narrative_id: int,
            user_input: str,
            story_dialogues: list[StoryDialogue],
    ) -> StoryTurnRetrieve:
        return self.story_turn_service.create(
            session_narrative_id=session_narrative_id,
            user_input=user_input,
            story_dialogues=story_dialogues,
        )

    def get_story_turn(
            self,
            resource_id: int,
    ) -> StoryTurnRetrieve:
        return self.story_turn_service.get(resource_id)

    def list_story_turns(
            self,
            search_term: str | None = None,
            session_narrative_id: int | None = None,
    ) -> list[StoryTurnList]:
        return self.story_turn_service.list(
            search_term=search_term,
            session_narrative_id=session_narrative_id,
        )

    def update_story_turn(
            self,
            resource_id: int,
            **kwargs,
    ) -> StoryTurnRetrieve:
        return self.story_turn_service.update(
            resource_id, **kwargs
        )

    def delete_story_turn(
            self,
            resource_id: int,
    ) -> None:
        self.story_turn_service.delete(resource_id)
