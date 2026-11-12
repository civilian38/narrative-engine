"""SessionCharacter 삭제 정책 및 StoryDialogue 무결성 통합 테스트.

기존 tests/conftest.py의 engine fixture(임시 SQLite DB + Alembic migration)를 사용한다.

실행:
    uv run python -m pytest tests/test_session_character_dialogue.py -v

주의: migration이 최신 모델의 FK/Check/Unique 제약조건을 반영해야 한다.
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from narrative_engine.domain.models import (
    DialogueType,
    SessionCharacter,
    SessionNarrative,
    StoryDialogue,
    StoryTurn,
)


def create_story_data(engine, *, with_dialogue=True, with_narration=True):
    """테스트용 이야기·캐릭터·턴·세그먼트를 생성하고 PK만 반환한다."""
    with engine.database.session() as session:
        narrative = SessionNarrative(
            title="테스트 이야기",
            world_description="중세 판타지 세계",
            situation="성문 앞에서 두 사람이 대치한다.",
        )
        character = SessionCharacter(
            name="아서",
            background_description="왕국의 기사",
            status="건강함",
            session_narrative=narrative,
        )
        turn = StoryTurn(
            turn_index=0,
            user_input="성문이 열린다.",
            session_narrative=narrative,
        )
        session.add_all([narrative, character, turn])
        session.flush()

        dialogues = []
        if with_narration:
            dialogues.append(
                StoryDialogue(
                    story_turn=turn,
                    position=len(dialogues),
                    kind=DialogueType.Narration,
                    content="성문이 천천히 열렸다.",
                    speaker_id=None,
                )
            )
        if with_dialogue:
            dialogues.append(
                StoryDialogue(
                    story_turn=turn,
                    position=len(dialogues),
                    kind=DialogueType.Dialogue,
                    content="누구냐!",
                    speaker=character,
                )
            )
        session.add_all(dialogues)
        session.flush()

        return {
            "narrative_id": narrative.id,
            "character_id": character.id,
            "turn_id": turn.id,
            "dialogue_ids": [item.id for item in dialogues],
        }


def assert_fk_enabled(engine):
    with engine.database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_foreign_keys_are_enabled(engine):
    assert_fk_enabled(engine)


def test_story_dialogues_are_ordered_and_have_correct_speakers(engine):
    data = create_story_data(engine)

    with engine.database.session() as session:
        turn = session.get(StoryTurn, data["turn_id"])
        assert turn is not None
        assert [segment.position for segment in turn.story_dialogues] == [0, 1]
        assert [segment.kind for segment in turn.story_dialogues] == [
            DialogueType.Narration,
            DialogueType.Dialogue,
        ]
        assert turn.story_dialogues[0].speaker_id is None
        assert turn.story_dialogues[1].speaker_id == data["character_id"]


def test_delete_character_without_dialogue_succeeds(engine):
    data = create_story_data(engine, with_dialogue=False)

    with engine.database.session() as session:
        character = session.get(SessionCharacter, data["character_id"])
        session.delete(character)

    with engine.database.session() as session:
        assert session.get(SessionCharacter, data["character_id"]) is None
        assert session.get(SessionNarrative, data["narrative_id"]) is not None
        assert session.get(StoryTurn, data["turn_id"]) is not None
        assert session.scalar(select(func.count()).select_from(StoryDialogue)) == 1


def test_delete_character_referenced_by_dialogue_is_rejected(engine):
    data = create_story_data(engine)

    # 지연된 NO ACTION FK: flush는 통과할 수 있으나 commit에서 실패해야 한다.
    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            character = session.get(SessionCharacter, data["character_id"])
            session.delete(character)

    # 실패한 트랜잭션은 롤백되므로 캐릭터와 대사가 유지된다.
    with engine.database.session() as session:
        assert session.get(SessionCharacter, data["character_id"]) is not None
        for dialogue_id in data["dialogue_ids"]:
            assert session.get(StoryDialogue, dialogue_id) is not None


def test_delete_character_after_removing_its_dialogue_succeeds(engine):
    data = create_story_data(engine)

    with engine.database.session() as session:
        character = session.get(SessionCharacter, data["character_id"])
        dialogue = session.scalar(
            select(StoryDialogue).where(
                StoryDialogue.story_turn_id == data["turn_id"],
                StoryDialogue.kind == DialogueType.Dialogue,
            )
        )
        session.delete(dialogue)
        session.delete(character)

    with engine.database.session() as session:
        assert session.get(SessionCharacter, data["character_id"]) is None
        remaining = session.scalars(
            select(StoryDialogue).where(StoryDialogue.story_turn_id == data["turn_id"])
        ).all()
        assert len(remaining) == 1
        assert remaining[0].kind == DialogueType.Narration
        assert remaining[0].speaker_id is None


def test_delete_turn_cascades_to_dialogues_but_keeps_character(engine):
    data = create_story_data(engine)

    with engine.database.session() as session:
        session.delete(session.get(StoryTurn, data["turn_id"]))

    with engine.database.session() as session:
        assert session.get(StoryTurn, data["turn_id"]) is None
        assert session.get(SessionCharacter, data["character_id"]) is not None
        for dialogue_id in data["dialogue_ids"]:
            assert session.get(StoryDialogue, dialogue_id) is None


@pytest.mark.parametrize("load_relationships", [False, True])
def test_delete_narrative_cascades_to_characters_turns_and_dialogues(
    engine, load_relationships
):
    data = create_story_data(engine)

    with engine.database.session() as session:
        narrative = session.get(SessionNarrative, data["narrative_id"])
        if load_relationships:
            # ORM에 관계들이 이미 로드된 경우도 확인한다.
            assert len(narrative.session_characters) == 1
            assert len(narrative.story_turns) == 1
            assert len(narrative.story_turns[0].story_dialogues) == 2
        session.delete(narrative)

    with engine.database.session() as session:
        assert session.get(SessionNarrative, data["narrative_id"]) is None
        assert session.get(SessionCharacter, data["character_id"]) is None
        assert session.get(StoryTurn, data["turn_id"]) is None
        for dialogue_id in data["dialogue_ids"]:
            assert session.get(StoryDialogue, dialogue_id) is None


@pytest.mark.parametrize(
    ("kind", "speaker_mode"),
    [
        (DialogueType.Dialogue, "null"),
        (DialogueType.Narration, "character"),
    ],
)
def test_kind_speaker_check_constraint(engine, kind, speaker_mode):
    data = create_story_data(engine, with_dialogue=False, with_narration=False)

    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            segment = StoryDialogue(
                story_turn_id=data["turn_id"],
                position=0,
                kind=kind,
                speaker_id=(
                    data["character_id"] if speaker_mode == "character" else None
                ),
                content="잘못된 화자 조건",
            )
            session.add(segment)
            session.flush()


def test_duplicate_dialogue_position_is_rejected(engine):
    data = create_story_data(engine)

    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            session.add(
                StoryDialogue(
                    story_turn_id=data["turn_id"],
                    position=0,
                    kind=DialogueType.Narration,
                    content="중복된 위치",
                    speaker_id=None,
                )
            )
            session.flush()


def test_negative_dialogue_position_is_rejected(engine):
    data = create_story_data(engine)

    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            session.add(
                StoryDialogue(
                    story_turn_id=data["turn_id"],
                    position=-1,
                    kind=DialogueType.Narration,
                    content="음수 위치",
                    speaker_id=None,
                )
            )
            session.flush()
