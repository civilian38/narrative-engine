from types import TracebackType

from narrative_engine.domain.models import SessionDialogue, DialogueType
from narrative_engine.domain.schemas.session_character import (
    SessionCharacterRetrieve,
    SessionCharacterList,
)
from narrative_engine.domain.schemas.session_character_opinion import SessionCharacterOpinionRetrieve, \
    SessionCharacterOpinionList
from narrative_engine.domain.schemas.session_character_memory import (
    SessionCharacterMemoryRetrieve,
    SessionCharacterMemoryList,
)
from narrative_engine.domain.schemas.session_dialogue import SessionDialogueRetrieve, SessionDialogueList
from narrative_engine.domain.schemas.session_turn import SessionTurnRetrieve, SessionTurnList
from narrative_engine.domain.schemas.llm_io import (
    CharacterUpdateResponse,
    StoryCreationResponse,
)
from narrative_engine.services.session_character_opinion_service import SessionCharacterOpinionService
from narrative_engine.services.session_character_memory_service import SessionCharacterMemoryService
from narrative_engine.services.session_character_service import SessionCharacterService
from typing import Self

from narrative_engine.domain.database import Database
from narrative_engine.domain.schemas.template_narrative import (
    TemplateNarrativeRetrieve,
    TemplateNarrativeList,
)
from narrative_engine.domain.schemas.template_character import (
    TemplateCharacterRetrieve,
    TemplateCharacterList,
)
from narrative_engine.domain.schemas.session_narrative import (
    SessionNarrativeRetrieve,
    SessionNarrativeList,
)
from narrative_engine.services.template_narrative_service import (
    TemplateNarrativeService,
)
from narrative_engine.services.template_character_service import (
    TemplateCharacterService,
)
from narrative_engine.services.session_narrative_service import (
    SessionNarrativeService,
)
from narrative_engine.services.session_dialogue_service import (
    SessionDialogueService
)
from narrative_engine.services.llm_service import LLMService
from narrative_engine.services.session_turn_service import (
    SessionTurnService
)


class NarrativeEngine:
    """Public facade for narrative engine operations."""

    def __init__(self, db_path: str = "narrative.db") -> None:
        self.database = Database(db_path)
        self.template_narrative_service = TemplateNarrativeService(
            self.database
        )
        self.template_character_service = TemplateCharacterService(
            self.database
        )
        self.session_narrative_service = SessionNarrativeService(
            self.database
        )
        self.session_character_service = SessionCharacterService(
            self.database
        )
        self.session_character_opinion_service = (
            SessionCharacterOpinionService(self.database)
        )
        self.session_character_memory_service = SessionCharacterMemoryService(
            self.database
        )
        self.session_turn_service = SessionTurnService(
            self.database
        )
        self.session_dialogue_service = SessionDialogueService(
            self.database
        )
        self.llm_service = LLMService(self.database)

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

    def create_template_narrative(
        self,
        name: str,
        world_description: str,
        initial_situation: str,
        template_description: str | None = None,
    ) -> TemplateNarrativeRetrieve:
        return self.template_narrative_service.create(
            name=name,
            world_description=world_description,
            initial_situation=initial_situation,
            template_description=template_description,
        )

    def get_template_narrative(
        self,
        resource_id: int,
    ) -> TemplateNarrativeRetrieve:
        return self.template_narrative_service.get(resource_id)

    def list_template_narratives(
        self,
        search_term: str | None = None,
    ) -> list[TemplateNarrativeList]:
        return self.template_narrative_service.list(search_term)

    def update_template_narrative(
        self,
        resource_id: int,
        **kwargs,
    ) -> TemplateNarrativeRetrieve:
        return self.template_narrative_service.update(
            resource_id, **kwargs
        )

    def delete_template_narrative(
        self,
        resource_id: int,
    ) -> None:
        self.template_narrative_service.delete(resource_id)

    # Character templates

    def create_template_character(
        self,
        template_narrative_id: int,
        name: str,
        background_description: str,
        initial_status: str,
    ) -> TemplateCharacterRetrieve:
        return self.template_character_service.create(
            template_narrative_id=template_narrative_id,
            name=name,
            background_description=background_description,
            initial_status=initial_status,
        )

    def get_template_character(
        self,
        resource_id: int,
    ) -> TemplateCharacterRetrieve:
        return self.template_character_service.get(resource_id)

    def list_template_characters(
        self,
        search_term: str | None = None,
    ) -> list[TemplateCharacterList]:
        return self.template_character_service.list(search_term)

    def update_template_character(
        self,
        resource_id: int,
        **kwargs,
    ) -> TemplateCharacterRetrieve:
        return self.template_character_service.update(
            resource_id, **kwargs
        )

    def delete_template_character(
        self,
        resource_id: int,
    ) -> None:
        self.template_character_service.delete(resource_id)

    # Session narratives

    def create_session_narrative(
        self,
        template_narrative_id: int,
        title: str | None = None,
    ) -> SessionNarrativeRetrieve:
        return self.session_narrative_service.create(
            template_narrative_id=template_narrative_id,
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

    # Session character opinions

    def create_session_character_opinion(
        self,
        session_narrative_id: int,
        from_character_id: int,
        to_character_id: int,
        opinion: str,
    ) -> SessionCharacterOpinionRetrieve:

        return self.session_character_opinion_service.create(
            session_narrative_id=session_narrative_id,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            opinion=opinion,
        )

    def get_session_character_opinion(
        self,
        resource_id: int,
    ) -> SessionCharacterOpinionRetrieve:

        return self.session_character_opinion_service.get(
            resource_id
        )

    def list_session_character_opinions(
        self,
        session_narrative_id: int,
        character_id: int | None = None,
    ) -> list[SessionCharacterOpinionList]:

        return self.session_character_opinion_service.list(
            session_narrative_id=session_narrative_id,
            character_id=character_id,
        )

    def update_session_character_opinion(
        self,
        resource_id: int,
        **kwargs,
    ) -> SessionCharacterOpinionRetrieve:

        return self.session_character_opinion_service.update(
            resource_id,
            **kwargs,
        )

    def delete_session_character_opinion(
        self,
        resource_id: int,
    ) -> None:

        self.session_character_opinion_service.delete(
            resource_id
        )

    # Session character memories

    def create_session_character_memory(
        self,
        session_character_id: int,
        session_turn_id: int,
        memory: str,
    ) -> SessionCharacterMemoryRetrieve:
        return self.session_character_memory_service.create(
            session_character_id=session_character_id,
            session_turn_id=session_turn_id,
            memory=memory,
        )

    def get_session_character_memory(
        self,
        resource_id: int,
    ) -> SessionCharacterMemoryRetrieve:
        return self.session_character_memory_service.get(resource_id)

    def list_session_character_memories_for_character(
        self,
        session_character_id: int,
    ) -> list[SessionCharacterMemoryList]:
        return self.session_character_memory_service.list_for_character(
            session_character_id
        )

    def list_session_character_memories_for_turn(
        self,
        session_turn_id: int,
    ) -> list[SessionCharacterMemoryList]:
        return self.session_character_memory_service.list_for_turn(
            session_turn_id
        )

    def update_session_character_memory(
        self,
        resource_id: int,
        **kwargs,
    ) -> SessionCharacterMemoryRetrieve:
        return self.session_character_memory_service.update(
            resource_id,
            **kwargs,
        )

    def delete_session_character_memory(
        self,
        resource_id: int,
    ) -> None:
        self.session_character_memory_service.delete(resource_id)

    # Story turns

    def create_session_turn(
            self,
            session_narrative_id: int,
            user_input: str,
            session_dialogues: list[SessionDialogue],
    ) -> SessionTurnRetrieve:
        return self.session_turn_service.create(
            session_narrative_id=session_narrative_id,
            user_input=user_input,
            session_dialogues=session_dialogues,
        )

    def get_session_turn(
            self,
            resource_id: int,
    ) -> SessionTurnRetrieve:
        return self.session_turn_service.get(resource_id)

    def list_session_turns(
            self,
            search_term: str | None = None,
            session_narrative_id: int | None = None,
    ) -> list[SessionTurnList]:
        return self.session_turn_service.list(
            search_term=search_term,
            session_narrative_id=session_narrative_id,
        )

    def update_session_turn(
            self,
            resource_id: int,
            **kwargs,
    ) -> SessionTurnRetrieve:
        return self.session_turn_service.update(
            resource_id, **kwargs
        )

    def delete_session_turn(
            self,
            resource_id: int,
    ) -> None:
        self.session_turn_service.delete(resource_id)

    # Story dialogues

    def create_session_dialogue(
        self,
        session_turn_id: int,
        content: str,
        position: int,
        kind: DialogueType,
        speaker_id: int | None = None,
    ) -> SessionDialogueRetrieve:
        return self.session_dialogue_service.create(
            session_turn_id=session_turn_id,
            content=content,
            position=position,
            kind=kind,
            speaker_id=speaker_id,
        )

    def get_session_dialogue(
        self,
        resource_id: int,
    ) -> SessionDialogueRetrieve:
        return self.session_dialogue_service.get(resource_id)

    def list_session_dialogues_for_turn(
        self,
        session_turn_id: int,
        search_term: str | None = None,
    ) -> list[SessionDialogueList]:
        return self.session_dialogue_service.list_for_session_turn(
            session_turn_id=session_turn_id,
            search_term=search_term,
        )

    def list_session_dialogues_for_session_narrative(
        self,
        session_narrative_id: int,
        search_term: str | None = None,
    ) -> list[SessionDialogueList]:
        return self.session_dialogue_service.list_for_session_narrative(
            session_narrative_id=session_narrative_id,
            search_term=search_term,
        )

    def update_session_dialogue(
        self,
        resource_id: int,
        **kwargs,
    ) -> SessionDialogueRetrieve:
        return self.session_dialogue_service.update(
            resource_id, **kwargs
        )

    def delete_session_dialogue(
        self,
        resource_id: int,
    ) -> None:
        self.session_dialogue_service.delete(resource_id)

    # LLM prompts and generated results

    def create_story_prompt(
        self,
        session_narrative_id: int,
        user_input: str,
    ) -> str:
        return self.llm_service.create_story_prompt(
            session_story_id=session_narrative_id,
            user_input=user_input,
        )

    def push_story_creation_result(
        self,
        session_narrative_id: int,
        user_input: str,
        creation_result: StoryCreationResponse,
    ) -> SessionTurnRetrieve:
        return self.llm_service.push_story_creation_result(
            session_narrative_id=session_narrative_id,
            user_input=user_input,
            creation_result=creation_result,
        )

    def create_character_update_prompt(
        self,
        session_character_id: int,
    ) -> str:
        return self.llm_service.create_character_update_prompt(
            session_character_id=session_character_id,
        )

    def push_character_update_result(
        self,
        session_character_id: int,
        session_turn_id: int,
        creation_result: CharacterUpdateResponse,
    ) -> SessionCharacterRetrieve:
        return self.llm_service.push_character_update_result(
            session_character_id=session_character_id,
            session_turn_id=session_turn_id,
            creation_result=creation_result,
        )
