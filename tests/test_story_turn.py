
"""StoryTurn integration tests.

Uses the engine fixture from tests/conftest.py.

Run:
    uv run python -m pytest tests/test_story_turn.py -v
"""

import pytest
from pydantic import ValidationError

from narrative_engine.engine import NarrativeEngine
from narrative_engine.domain.models import (
    DialogueType,
    StoryDialogue,
)
from narrative_engine.domain.schemas.story_turn import (
    StoryTurnCreate,
    StoryTurnRetrieve,
    StoryTurnList,
)
from narrative_engine.exceptions import (
    ResourceNotFoundError,
    InvalidOperationError,
)


# Test data helpers

def create_sample_session(engine):
    template = engine.create_narrative_template(
        name="Alien Invasion",
        world_description="외계인이 침략한 지구",
        initial_situation="Sarah는 폐허에서 깨어났다.",
    )
    return engine.create_session_narrative(template.id)


def create_sample_turn(
    engine,
    session_narrative_id,
    user_input="주변을 살펴본다.",
    story_dialogues=None,
):
    return engine.create_story_turn(
        session_narrative_id=session_narrative_id,
        user_input=user_input,
        story_dialogues=(
            story_dialogues if story_dialogues is not None else []
        ),
    )


def create_sample_character(engine, session_narrative_id):
    return engine.create_session_character(
        session_narrative_id=session_narrative_id,
        name="Sarah",
        background_description="외계인 침공의 생존자",
        status="건강함",
    )


# CREATE

def test_create_story_turn(engine):
    narrative = create_sample_session(engine)

    created = create_sample_turn(engine, narrative.id)

    assert isinstance(created, StoryTurnRetrieve)
    assert isinstance(created.id, int)
    assert created.id > 0
    assert created.session_narrative_id == narrative.id
    assert created.turn_index == 0
    assert created.user_input == "주변을 살펴본다."
    assert created.story_dialogues == []


def test_create_story_turn_with_dialogues(engine):
    narrative = create_sample_session(engine)
    character = create_sample_character(engine, narrative.id)

    dialogues = [
        StoryDialogue(
            position=0,
            kind=DialogueType.Narration,
            content="Sarah는 주변을 둘러보았다.",
            speaker_id=None,
        ),
        StoryDialogue(
            position=1,
            kind=DialogueType.Dialogue,
            content="여기가 어디지?",
            speaker_id=character.id,
        ),
    ]

    created = create_sample_turn(
        engine,
        narrative.id,
        user_input="주변을 살펴본다.",
        story_dialogues=dialogues,
    )

    retrieved = engine.get_story_turn(created.id)

    assert len(retrieved.story_dialogues) == 2
    assert [d.position for d in retrieved.story_dialogues] == [0, 1]
    assert retrieved.story_dialogues[0].kind == DialogueType.Narration
    assert retrieved.story_dialogues[0].speaker_id is None
    assert retrieved.story_dialogues[1].kind == DialogueType.Dialogue
    assert retrieved.story_dialogues[1].speaker_id == character.id

    assert all(
        dialogue.id > 0
        for dialogue in retrieved.story_dialogues
    )

    with engine.database.session() as session:
        for dialogue in retrieved.story_dialogues:
            saved = session.get(StoryDialogue, dialogue.id)

            assert saved is not None
            assert saved.story_turn_id == created.id


def test_create_story_turn_auto_index(engine):
    narrative = create_sample_session(engine)

    first = create_sample_turn(engine, narrative.id, "첫 번째 행동")
    second = create_sample_turn(engine, narrative.id, "두 번째 행동")
    third = create_sample_turn(engine, narrative.id, "세 번째 행동")

    assert [first.turn_index, second.turn_index, third.turn_index] == [
        0, 1, 2
    ]


def test_story_turn_index_is_independent_per_session(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    first = create_sample_turn(engine, first_session.id)
    second = create_sample_turn(engine, first_session.id)
    other = create_sample_turn(engine, second_session.id)

    assert first.turn_index == 0
    assert second.turn_index == 1
    assert other.turn_index == 0


def test_create_story_turn_with_missing_session(engine):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        create_sample_turn(engine, nonexistent_id)

    assert exc_info.value.resource == "SessionNarrative"
    assert exc_info.value.resource_id == nonexistent_id
    assert engine.list_story_turns() == []


def test_story_turn_create_schema_invalid_index():
    with pytest.raises(ValidationError):
        StoryTurnCreate(
            session_narrative_id=1,
            turn_index=-1,
            user_input="잘못된 턴",
        )


def test_create_story_turn_invalid_user_input(engine):
    narrative = create_sample_session(engine)

    with pytest.raises(ValidationError):
        create_sample_turn(engine, narrative.id, user_input=None)

    assert engine.list_story_turns() == []


# READ

def test_get_story_turn(engine):
    narrative = create_sample_session(engine)
    created = create_sample_turn(engine, narrative.id)

    retrieved = engine.get_story_turn(created.id)

    assert isinstance(retrieved, StoryTurnRetrieve)
    assert retrieved.model_dump() == created.model_dump()


def test_get_story_turn_dialogues_ordered(engine):
    narrative = create_sample_session(engine)

    created = create_sample_turn(
        engine,
        narrative.id,
        story_dialogues=[
            StoryDialogue(
                position=2,
                kind=DialogueType.Narration,
                content="세 번째 문장",
            ),
            StoryDialogue(
                position=0,
                kind=DialogueType.Narration,
                content="첫 번째 문장",
            ),
            StoryDialogue(
                position=1,
                kind=DialogueType.Narration,
                content="두 번째 문장",
            ),
        ],
    )

    retrieved = engine.get_story_turn(created.id)

    assert [d.position for d in retrieved.story_dialogues] == [0, 1, 2]
    assert [d.content for d in retrieved.story_dialogues] == [
        "첫 번째 문장",
        "두 번째 문장",
        "세 번째 문장",
    ]


# LIST

def test_list_story_turns(engine):
    narrative = create_sample_session(engine)

    first = create_sample_turn(engine, narrative.id, "첫 번째")
    second = create_sample_turn(engine, narrative.id, "두 번째")
    third = create_sample_turn(engine, narrative.id, "세 번째")

    turns = engine.list_story_turns()

    assert len(turns) == 3
    assert all(isinstance(turn, StoryTurnList) for turn in turns)
    assert [turn.id for turn in turns] == [
        first.id, second.id, third.id
    ]
    assert [turn.turn_index for turn in turns] == [0, 1, 2]


def test_list_story_turn_fields(engine):
    narrative = create_sample_session(engine)
    create_sample_turn(engine, narrative.id)

    turn = engine.list_story_turns()[0]

    assert set(turn.model_dump()) == {
        "id",
        "turn_index",
        "user_input",
    }


def test_list_story_turns_filter_by_session(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    first = create_sample_turn(engine, first_session.id)
    second = create_sample_turn(engine, first_session.id)
    other = create_sample_turn(engine, second_session.id)

    results = engine.list_story_turns(
        session_narrative_id=first_session.id
    )

    assert [item.id for item in results] == [
        first.id, second.id
    ]
    assert other.id not in [item.id for item in results]


# SEARCH

def test_search_story_turns(engine):
    narrative = create_sample_session(engine)

    create_sample_turn(engine, narrative.id, "문을 연다")
    create_sample_turn(engine, narrative.id, "문을 닫는다")
    create_sample_turn(engine, narrative.id, "주변을 살펴본다")

    results = engine.list_story_turns(
        search_term="  문을  "
    )

    assert len(results) == 2
    assert {turn.user_input for turn in results} == {
        "문을 연다",
        "문을 닫는다",
    }


@pytest.mark.parametrize("search_term", [None, "", "   "])
def test_search_story_turns_with_empty_term(engine, search_term):
    narrative = create_sample_session(engine)
    create_sample_turn(engine, narrative.id, "첫 번째")
    create_sample_turn(engine, narrative.id, "두 번째")

    results = engine.list_story_turns(search_term=search_term)

    assert len(results) == 2


def test_search_story_turns_with_session_filter(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    matching = create_sample_turn(
        engine, first_session.id, "문을 연다"
    )
    create_sample_turn(engine, first_session.id, "기다린다")
    create_sample_turn(engine, second_session.id, "문을 닫는다")

    results = engine.list_story_turns(
        search_term="문을",
        session_narrative_id=first_session.id,
    )

    assert [turn.id for turn in results] == [matching.id]


# UPDATE

def test_update_story_turn(engine):
    narrative = create_sample_session(engine)
    created = create_sample_turn(engine, narrative.id)

    updated = engine.update_story_turn(
        created.id,
        user_input="새로운 행동을 선택한다.",
    )

    assert isinstance(updated, StoryTurnRetrieve)
    assert updated.id == created.id
    assert updated.turn_index == created.turn_index
    assert updated.session_narrative_id == narrative.id
    assert updated.user_input == "새로운 행동을 선택한다."

    retrieved = engine.get_story_turn(created.id)
    assert retrieved.user_input == "새로운 행동을 선택한다."


def test_update_story_turn_preserves_dialogues(engine):
    narrative = create_sample_session(engine)

    created = create_sample_turn(
        engine,
        narrative.id,
        story_dialogues=[
            StoryDialogue(
                position=0,
                kind=DialogueType.Narration,
                content="기존 내레이션",
            ),
        ],
    )

    updated = engine.update_story_turn(
        created.id,
        user_input="수정된 행동",
    )

    assert len(updated.story_dialogues) == 1
    assert updated.story_dialogues[0].content == "기존 내레이션"
    assert engine.get_story_turn(created.id).story_dialogues == (
        updated.story_dialogues
    )


def test_update_story_turn_without_changes(engine):
    narrative = create_sample_session(engine)
    created = create_sample_turn(engine, narrative.id)

    updated = engine.update_story_turn(created.id)

    assert updated.model_dump() == created.model_dump()


@pytest.mark.parametrize(
    ("changes", "expected_exception"),
    [
        ({"user_input": None}, InvalidOperationError),
        ({"turn_index": None}, ValidationError),
        ({"turn_index": 5}, ValidationError),
        ({"turn_index": -1}, ValidationError),
        ({"unknown_field": "value"}, ValidationError),
        ({"session_narrative_id": 999}, ValidationError),
    ],
)
def test_update_story_turn_invalid_data(
    engine, changes, expected_exception
):
    narrative = create_sample_session(engine)
    created = create_sample_turn(engine, narrative.id)

    with pytest.raises(expected_exception):
        engine.update_story_turn(created.id, **changes)

    assert engine.get_story_turn(created.id) == created


def test_update_story_turn_index_is_immutable(engine):
    narrative = create_sample_session(engine)

    first = create_sample_turn(engine, narrative.id)
    second = create_sample_turn(engine, narrative.id)

    with pytest.raises(ValidationError):
        engine.update_story_turn(
            second.id,
            turn_index=first.turn_index,
        )

    assert engine.get_story_turn(first.id).turn_index == 0
    assert engine.get_story_turn(second.id).turn_index == 1


# DELETE

def test_delete_story_turn(engine):
    narrative = create_sample_session(engine)
    first = create_sample_turn(engine, narrative.id)
    second = create_sample_turn(engine, narrative.id)

    engine.delete_story_turn(first.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_story_turn(first.id)

    assert engine.get_story_turn(second.id).id == second.id
    assert [turn.id for turn in engine.list_story_turns()] == [
        second.id
    ]


def test_delete_story_turn_cascades_dialogues(engine):
    narrative = create_sample_session(engine)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_turn(
        engine,
        narrative.id,
        story_dialogues=[
            StoryDialogue(
                position=0,
                kind=DialogueType.Narration,
                content="바람이 불었다.",
            ),
            StoryDialogue(
                position=1,
                kind=DialogueType.Dialogue,
                content="누구냐!",
                speaker_id=character.id,
            ),
        ],
    )

    dialogue_ids = [
        dialogue.id for dialogue in created.story_dialogues
    ]

    engine.delete_story_turn(created.id)

    with engine.database.session() as session:
        for dialogue_id in dialogue_ids:
            assert session.get(StoryDialogue, dialogue_id) is None

    # The narrative and its character must remain.
    assert engine.get_session_narrative(narrative.id).id == narrative.id
    assert engine.get_session_character(character.id).id == character.id


def test_delete_session_cascades_story_turns(engine):
    narrative = create_sample_session(engine)

    first = create_sample_turn(engine, narrative.id)
    second = create_sample_turn(engine, narrative.id)

    engine.delete_session_narrative(narrative.id)

    for turn in [first, second]:
        with pytest.raises(ResourceNotFoundError):
            engine.get_story_turn(turn.id)


# NOT FOUND

@pytest.mark.parametrize("operation", ["get", "update", "delete"])
def test_story_turn_not_found(engine, operation):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        if operation == "get":
            engine.get_story_turn(nonexistent_id)
        elif operation == "update":
            engine.update_story_turn(
                nonexistent_id,
                user_input="Updated",
            )
        else:
            engine.delete_story_turn(nonexistent_id)

    assert exc_info.value.resource == "StoryTurn"
    assert exc_info.value.resource_id == nonexistent_id


# TURN INDEX REGRESSION

def test_create_after_deleting_middle_turn(engine):
    narrative = create_sample_session(engine)

    first = create_sample_turn(engine, narrative.id, "첫 번째")
    second = create_sample_turn(engine, narrative.id, "두 번째")
    third = create_sample_turn(engine, narrative.id, "세 번째")

    engine.delete_story_turn(second.id)

    fourth = create_sample_turn(engine, narrative.id, "네 번째")

    assert fourth.turn_index == 3
    assert [
        turn.turn_index
        for turn in engine.list_story_turns(
            session_narrative_id=narrative.id
        )
    ] == [0, 2, 3]

    assert engine.get_story_turn(first.id).id == first.id
    assert engine.get_story_turn(third.id).id == third.id


# PERSISTENCE

def test_story_turn_persistence(tmp_path):
    db_path = str(tmp_path / "story_turn_persistence.db")

    first_engine = NarrativeEngine(db_path)
    try:
        first_engine.initialize()
        narrative = create_sample_session(first_engine)

        created = create_sample_turn(
            first_engine,
            narrative.id,
            user_input="문을 연다.",
            story_dialogues=[
                StoryDialogue(
                    position=0,
                    kind=DialogueType.Narration,
                    content="문이 천천히 열렸다.",
                ),
            ],
        )

        turn_id = created.id
        narrative_id = narrative.id
    finally:
        first_engine.close()

    second_engine = NarrativeEngine(db_path)
    try:
        second_engine.initialize()

        retrieved = second_engine.get_story_turn(turn_id)

        assert retrieved.id == turn_id
        assert retrieved.session_narrative_id == narrative_id
        assert retrieved.turn_index == 0
        assert retrieved.user_input == "문을 연다."
        assert len(retrieved.story_dialogues) == 1
        assert retrieved.story_dialogues[0].content == (
            "문이 천천히 열렸다."
        )
    finally:
        second_engine.close()
