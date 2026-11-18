from typing import cast

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from narrative_engine.domain.database import Database
from narrative_engine.domain.models import (
    SessionCharacter,
    SessionNarrative,
    SessionTurn, DialogueType, SessionDialogue, SessionCharacterOpinion,
)
from narrative_engine.domain.schemas.llm_io import StoryCreationResponse, DialogueOutput, CharacterUpdateResponse
from narrative_engine.domain.schemas.session_character_opinion import SessionCharacterOpinionCreate
from narrative_engine.domain.schemas.session_dialogue import SessionDialogueCreate
from narrative_engine.domain.schemas.session_turn import SessionTurnCreate
from narrative_engine.exceptions import ResourceNotFoundError, InvalidOperationError
from narrative_engine.services.session_dialogue_service import SessionDialogueService


class LLMService:
    """Build prompts for story and character-state generation."""

    def __init__(self, database: Database):
        self.database = database

    def create_story_prompt(
        self,
        session_story_id: int,
        user_input: str,
    ) -> str:
        """Create a story-generation prompt from the current session state."""
        with self.database.session() as session:
            story = session.get(
                SessionNarrative,
                session_story_id,
                options=[
                    selectinload(SessionNarrative.session_characters).selectinload(
                        SessionCharacter.opinions_to_others
                    ),
                    selectinload(SessionNarrative.session_turns)
                    .selectinload(SessionTurn.session_dialogues),
                ],
            )
            if story is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_story_id,
                )

            character_ids = [character.id for character in story.session_characters]
            character_text = "\n\n".join(
                character.to_prompt_text(
                    opinion_to_ids=[
                        character_id
                        for character_id in character_ids
                        if character_id != character.id
                    ]
                )
                for character in story.session_characters
            )
            history_text = "\n\n".join(
                turn.to_prompt_text(include_user_input=False)
                for turn in story.session_turns
            )
            allowed_id_pair = str(story.get_character_name_id_pairs())

            sections = [
                "아래 세계관의 현재 상태와 등장인물 정보를 바탕으로 이야기를 이어서 생성하라.",
                story.to_prompt_text(),
                "===등장인물 현재 상태===\n" + character_text,
                "===이전 이야기===\n" + (history_text or "(이전 이야기 없음)"),
                "===사용자 입력===\n" + user_input,
                "출력은 JSON 객체로 작성하고, 최상위 `contents` 배열에 순서대로 이야기 항목을, "
                "`new_world_situation` 문자열에 이번 사건 이후의 현재 상황을 넣어라.\n"
                "대사는 {\"kind\": \"Dialogue\", \"speaker_name\": 이름, \"speaker_id\": ID, \"content\": 내용} 형식, "
                "서술은 {\"kind\": \"Narration\", \"content\": 내용} 형식으로 작성하라. "
                "Dialogue는 해당 발화자의 이름과 ID를 정확히 사용하고, 인물의 발화가 아닌 서술은 Narration으로 작성하라.",
                "사용할 수 있는 ID 목록: " + allowed_id_pair
            ]
            return "\n\n".join(sections)

    def push_story_creation_result(
        self,
        session_narrative_id: int,
        user_input: str,
        creation_result: StoryCreationResponse
    ):
        with self.database.session() as session:
            story = session.get(
                SessionNarrative,
                session_narrative_id,
                options=[
                    selectinload(SessionNarrative.session_characters).selectinload(
                        SessionCharacter.opinions_to_others
                    ),
                    selectinload(SessionNarrative.session_turns)
                    .selectinload(SessionTurn.session_dialogues),
                ],
            )
            if story is None:
                raise ResourceNotFoundError(
                    resource="SessionNarrative",
                    resource_id=session_narrative_id,
                )

            next_turn_index = session.scalar(
                select(func.max(SessionTurn.turn_index))
                .where(
                    SessionTurn.session_narrative_id == session_narrative_id
                )
            )

            next_turn_index = (
                next_turn_index + 1
                if next_turn_index is not None
                else 0
            )

            session_turn_data = SessionTurnCreate(
                turn_index=next_turn_index,
                user_input=user_input,
                session_narrative_id=session_narrative_id,
            )

            session_turn = SessionTurn(
                **session_turn_data.model_dump()
            )
            session.add(session_turn)
            session.flush()

            session_dialogue_data_list = [
                SessionDialogueCreate(
                    session_turn_id=session_turn.id,
                    content=content.content,
                    position=index,
                    kind=cast(DialogueType, cast(object, content.kind)),
                    speaker_id=content.speaker_id if isinstance(content, DialogueOutput) else None,
                ) for index, content in enumerate(creation_result.contents)
            ]
            for dialogue_data in session_dialogue_data_list:
                SessionDialogueService.validate_speaker(session, session_turn, dialogue_data.speaker_id)
                dialogue = SessionDialogue(**dialogue_data.model_dump())
                session.add(dialogue)

            story.situation = creation_result.new_world_situation

    def create_character_update_prompt(
        self,
        session_character_id: int,
    ) -> str:
        """Create a prompt to update one character from their perspective."""
        with self.database.session() as session:
            character = session.get(
                SessionCharacter,
                session_character_id,
                options=[
                    selectinload(SessionCharacter.opinions_to_others),
                    selectinload(SessionCharacter.session_narrative).selectinload(
                        SessionNarrative.session_turns
                    ).selectinload(SessionTurn.session_dialogues),
                ],
            )
            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=session_character_id,
                )

            story = character.session_narrative
            other_character_ids = [
                other.id
                for other in story.session_characters
                if other.id != character.id
            ]
            character_text = character.to_prompt_text(
                opinion_to_ids=other_character_ids,
                opinion_from_ids=None,
            )
            turns = story.session_turns
            history_parts = [
                turn.to_prompt_text(include_user_input=False)
                for turn in turns[:-1]
            ]
            if turns:
                history_parts.append(
                    "===이 시점을 기준으로 캐릭터의 상태를 변경하라===\n"
                    + turns[-1].to_prompt_text(include_user_input=False)
                )
            history_text = "\n\n".join(history_parts) or "(이전 이야기 없음)"

            return "\n\n".join(
                [
                    "아래 세계관과 이야기의 흐름을 고려하여, 지정된 인물의 관점에서 현재 상태를 갱신하라.",
                    story.to_prompt_text(),
                    "===상태를 갱신할 등장인물===\n" + character_text,
                    "===이전 이야기===\n" + history_text,
                    "이 인물이 직접 알 수 있는 정보만 사용하라. 다른 인물들의 현재 상태나 이 인물에 대한 그들의 의견은 입력에 포함되어 있지 않으며 추측하여 상태에 추가하지 말라.\n"
                    "출력은 JSON 객체로 작성하라: `new_status` 문자열과 `opinion_alter` 객체를 포함하고, "
                    "`opinion_alter`에는 `alter_data` 배열을 둔다. 배열에는 바뀐 의견만 "
                    "{\"target_character_name\": 이름, \"target_character_id\": ID, \"new_opinion\": 의견} 형식으로 넣어라. "
                    "바뀐 의견이 없으면 빈 배열을 사용하라.",
                ]
            )

    def push_character_update_result(
        self,
        session_character_id: int,
        creation_result: CharacterUpdateResponse
    ):
        with self.database.session() as session:
            character = session.get(
                SessionCharacter,
                session_character_id,
                options=[
                    selectinload(SessionCharacter.opinions_to_others),
                ],
            )
            if character is None:
                raise ResourceNotFoundError(
                    resource="SessionCharacter",
                    resource_id=session_character_id,
                )

            character.status = creation_result.new_status

            for alter_data in creation_result.opinion_alter.alter_data:
                opinion_to = next(
                    (opinion for opinion in character.opinions_to_others
                     if opinion.to_character_id == alter_data.target_character_id),
                    None,
                )

                if opinion_to is None:
                    to_character = session.get(SessionCharacter, alter_data.target_character_id)
                    if to_character is not None and to_character.session_narrative_id == character.session_narrative.id:
                        new_opinion_data = SessionCharacterOpinionCreate(
                            session_narrative_id=character.session_narrative.id,
                            from_character_id=session_character_id,
                            to_character_id=alter_data.target_character_id,
                            opinion=alter_data.new_opinion
                        )

                        new_opinion = SessionCharacterOpinion(**new_opinion_data.model_dump())
                        session.add(new_opinion)

                    else:
                        raise InvalidOperationError(
                            "Invalid character ID delivered from LLM response"
                        )
                else:
                    opinion_to.opinion = alter_data.new_opinion
