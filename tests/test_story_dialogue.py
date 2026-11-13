
"""StoryDialogue integration tests.

Uses the engine fixture from tests/conftest.py.

Run:
    uv run python -m pytest tests/test_story_dialogue.py -v
"""

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from narrative_engine.engine import NarrativeEngine
from narrative_engine.domain.models import (
    DialogueType,
    StoryDialogue,
)
from narrative_engine.domain.schemas.story_dialogue import (
    StoryDialogueCreate,
    StoryDialogueRetrieve,
    StoryDialogueList,
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


def create_sample_turn(engine, session_narrative_id):
    return engine.create_story_turn(
        session_narrative_id=session_narrative_id,
        user_input="주변을 살펴본다.",
        story_dialogues=[],
    )


def create_sample_character(
    engine,
    session_narrative_id,
    name="Sarah",
):
    return engine.create_session_character(
        session_narrative_id=session_narrative_id,
        name=name,
        background_description="외계인 침공의 생존자",
        status="건강함",
    )


def create_sample_dialogue(
    engine,
    story_turn_id,
    content="문이 천천히 열렸다.",
    position=0,
    kind=DialogueType.Narration,
    speaker_id=None,
):
    return engine.create_story_dialogue(
        story_turn_id=story_turn_id,
        content=content,
        position=position,
        kind=kind,
        speaker_id=speaker_id,
    )


# CREATE

def test_create_story_dialogue_narration(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
    )

    assert isinstance(created, StoryDialogueRetrieve)
    assert isinstance(created.id, int)
    assert created.id > 0
    assert created.story_turn_id == turn.id
    assert created.content == "문이 천천히 열렸다."
    assert created.position == 0
    assert created.kind == DialogueType.Narration
    assert created.speaker_id is None

    retrieved_turn = engine.get_story_turn(turn.id)
    assert len(retrieved_turn.story_dialogues) == 1
    assert retrieved_turn.story_dialogues[0].id == created.id


def test_create_story_dialogue_with_speaker(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="여기가 어디지?",
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    assert created.kind == DialogueType.Dialogue
    assert created.content == "여기가 어디지?"
    assert created.speaker_id == character.id
    assert created.story_turn_id == turn.id

    with engine.database.session() as session:
        saved = session.get(StoryDialogue, created.id)

        assert saved is not None
        assert saved.speaker_id == character.id


def test_create_story_dialogue_with_missing_turn(engine):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        create_sample_dialogue(
            engine,
            story_turn_id=nonexistent_id,
        )

    assert exc_info.value.resource == "StoryTurn"
    assert exc_info.value.resource_id == nonexistent_id


def test_create_story_dialogue_with_missing_speaker(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        create_sample_dialogue(
            engine,
            story_turn_id=turn.id,
            kind=DialogueType.Dialogue,
            speaker_id=999999,
        )

    assert exc_info.value.resource == "SessionCharacter"
    assert exc_info.value.resource_id == 999999

    assert engine.list_story_dialogues_for_turn(turn.id) == []


def test_create_story_dialogue_with_other_session_speaker(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    turn = create_sample_turn(engine, first_session.id)
    character = create_sample_character(
        engine,
        second_session.id,
    )

    with pytest.raises(InvalidOperationError):
        create_sample_dialogue(
            engine,
            story_turn_id=turn.id,
            kind=DialogueType.Dialogue,
            speaker_id=character.id,
        )

    assert engine.list_story_dialogues_for_turn(turn.id) == []


@pytest.mark.parametrize(
    ("kind", "speaker_id"),
    [
        (DialogueType.Dialogue, None),
        (DialogueType.Narration, 1),
    ],
)
def test_create_story_dialogue_invalid_speaker(
    engine,
    kind,
    speaker_id,
):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    with pytest.raises(InvalidOperationError):
        create_sample_dialogue(
            engine,
            story_turn_id=turn.id,
            kind=kind,
            speaker_id=speaker_id,
        )

    assert engine.list_story_dialogues_for_turn(turn.id) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"position": -1},
        {"position": None},
        {"content": None},
        {"kind": None},
        {"kind": "InvalidType"},
    ],
)
def test_create_story_dialogue_invalid_data(engine, changes):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    data = {
        "story_turn_id": turn.id,
        "content": "테스트 내레이션",
        "position": 0,
        "kind": DialogueType.Narration,
    }
    data.update(changes)

    with pytest.raises(ValidationError):
        engine.create_story_dialogue(**data)

    assert engine.list_story_dialogues_for_turn(turn.id) == []


def test_story_dialogue_create_schema_invalid_position():
    with pytest.raises(ValidationError):
        StoryDialogueCreate(
            story_turn_id=1,
            content="잘못된 위치",
            position=-1,
            kind=DialogueType.Narration,
        )


def test_create_story_dialogue_duplicate_position(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="첫 번째 문장",
        position=0,
    )

    with pytest.raises(IntegrityError):
        create_sample_dialogue(
            engine,
            story_turn_id=turn.id,
            content="중복된 위치",
            position=0,
        )

    results = engine.list_story_dialogues_for_turn(turn.id)

    assert len(results) == 1
    assert results[0].id == first.id


# READ

def test_get_story_dialogue(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
    )

    retrieved = engine.get_story_dialogue(created.id)

    assert isinstance(retrieved, StoryDialogueRetrieve)
    assert retrieved.model_dump() == created.model_dump()


# LIST FOR STORY TURN

def test_list_story_dialogues_for_turn(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    third = create_sample_dialogue(
        engine, turn.id, "세 번째 문장", position=2
    )
    first = create_sample_dialogue(
        engine, turn.id, "첫 번째 문장", position=0
    )
    second = create_sample_dialogue(
        engine, turn.id, "두 번째 문장", position=1
    )

    results = engine.list_story_dialogues_for_turn(turn.id)

    assert len(results) == 3
    assert all(
        isinstance(item, StoryDialogueList)
        for item in results
    )

    assert [item.id for item in results] == [
        first.id,
        second.id,
        third.id,
    ]
    assert [item.position for item in results] == [0, 1, 2]


def test_list_story_dialogue_fields(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    create_sample_dialogue(engine, turn.id)

    dialogue = engine.list_story_dialogues_for_turn(turn.id)[0]

    assert set(dialogue.model_dump()) == {
        "id",
        "story_turn_id",
        "content",
        "position",
        "kind",
        "speaker_id",
    }


def test_list_story_dialogues_for_turn_isolated(engine):
    narrative = create_sample_session(engine)

    first_turn = create_sample_turn(engine, narrative.id)
    second_turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine, first_turn.id, "첫 번째 턴", position=0
    )
    create_sample_dialogue(
        engine, second_turn.id, "두 번째 턴", position=0
    )

    results = engine.list_story_dialogues_for_turn(
        first_turn.id
    )

    assert [item.id for item in results] == [first.id]


# LIST FOR SESSION NARRATIVE

def test_list_story_dialogues_for_session_narrative(engine):
    narrative = create_sample_session(engine)

    first_turn = create_sample_turn(engine, narrative.id)
    second_turn = create_sample_turn(engine, narrative.id)

    second_line = create_sample_dialogue(
        engine, first_turn.id, "첫 턴의 두 번째 문장", 1
    )
    third_line = create_sample_dialogue(
        engine, second_turn.id, "두 번째 턴의 문장", 0
    )
    first_line = create_sample_dialogue(
        engine, first_turn.id, "첫 턴의 첫 번째 문장", 0
    )

    results = (
        engine.list_story_dialogues_for_session_narrative(
            narrative.id
        )
    )

    assert len(results) == 3
    assert all(
        isinstance(item, StoryDialogueList)
        for item in results
    )

    assert [item.id for item in results] == [
        first_line.id,
        second_line.id,
        third_line.id,
    ]

    assert [item.story_turn_id for item in results] == [
        first_turn.id,
        first_turn.id,
        second_turn.id,
    ]


def test_list_story_dialogues_for_session_isolated(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    first_turn = create_sample_turn(engine, first_session.id)
    second_turn = create_sample_turn(engine, second_session.id)

    first = create_sample_dialogue(
        engine, first_turn.id, "첫 번째 세션"
    )
    create_sample_dialogue(
        engine, second_turn.id, "두 번째 세션"
    )

    results = (
        engine.list_story_dialogues_for_session_narrative(
            first_session.id
        )
    )

    assert [item.id for item in results] == [first.id]


def test_list_story_dialogues_empty_results(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    assert engine.list_story_dialogues_for_turn(turn.id) == []
    assert (
        engine.list_story_dialogues_for_session_narrative(
            narrative.id
        ) == []
    )

    assert engine.list_story_dialogues_for_turn(999999) == []
    assert (
        engine.list_story_dialogues_for_session_narrative(
            999999
        ) == []
    )


# SEARCH

@pytest.mark.parametrize(
    "list_mode",
    ["turn", "session"],
)
def test_search_story_dialogues(engine, list_mode):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine, turn.id, "문이 열린다", position=0
    )
    second = create_sample_dialogue(
        engine, turn.id, "문이 닫힌다", position=1
    )
    create_sample_dialogue(
        engine, turn.id, "바람이 분다", position=2
    )

    if list_mode == "turn":
        results = engine.list_story_dialogues_for_turn(
            turn.id,
            search_term="  문이  ",
        )
    else:
        results = (
            engine.list_story_dialogues_for_session_narrative(
                narrative.id,
                search_term="  문이  ",
            )
        )

    assert [item.id for item in results] == [
        first.id,
        second.id,
    ]


@pytest.mark.parametrize("search_term", [None, "", "   "])
@pytest.mark.parametrize("list_mode", ["turn", "session"])
def test_search_story_dialogues_with_empty_term(
    engine,
    search_term,
    list_mode,
):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    create_sample_dialogue(
        engine, turn.id, "첫 번째", position=0
    )
    create_sample_dialogue(
        engine, turn.id, "두 번째", position=1
    )

    if list_mode == "turn":
        results = engine.list_story_dialogues_for_turn(
            turn.id,
            search_term=search_term,
        )
    else:
        results = (
            engine.list_story_dialogues_for_session_narrative(
                narrative.id,
                search_term=search_term,
            )
        )

    assert len(results) == 2


def test_search_story_dialogues_respects_scope(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    first_turn = create_sample_turn(engine, first_session.id)
    another_turn = create_sample_turn(engine, first_session.id)
    other_session_turn = create_sample_turn(
        engine, second_session.id
    )

    matching = create_sample_dialogue(
        engine, first_turn.id, "문을 연다"
    )
    create_sample_dialogue(
        engine, another_turn.id, "기다린다"
    )
    create_sample_dialogue(
        engine, other_session_turn.id, "문을 닫는다"
    )

    turn_results = engine.list_story_dialogues_for_turn(
        first_turn.id,
        search_term="문을",
    )
    session_results = (
        engine.list_story_dialogues_for_session_narrative(
            first_session.id,
            search_term="문을",
        )
    )

    assert [item.id for item in turn_results] == [matching.id]
    assert [item.id for item in session_results] == [
        matching.id
    ]


# UPDATE

def test_update_story_dialogue(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(engine, turn.id)

    updated = engine.update_story_dialogue(
        created.id,
        content="새로운 내레이션",
        position=2,
    )

    assert isinstance(updated, StoryDialogueRetrieve)
    assert updated.id == created.id
    assert updated.story_turn_id == turn.id
    assert updated.content == "새로운 내레이션"
    assert updated.position == 2
    assert updated.kind == DialogueType.Narration
    assert updated.speaker_id is None

    retrieved = engine.get_story_dialogue(created.id)

    assert retrieved.model_dump() == updated.model_dump()


def test_update_story_dialogue_content_only(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="안녕?",
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    updated = engine.update_story_dialogue(
        created.id,
        content="거기 누구 있어?",
    )

    assert updated.content == "거기 누구 있어?"
    assert updated.position == created.position
    assert updated.kind == DialogueType.Dialogue
    assert updated.speaker_id == character.id


def test_update_story_dialogue_speaker(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first_character = create_sample_character(
        engine, narrative.id, "Sarah"
    )
    second_character = create_sample_character(
        engine, narrative.id, "John"
    )

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="안녕",
        kind=DialogueType.Dialogue,
        speaker_id=first_character.id,
    )

    updated = engine.update_story_dialogue(
        created.id,
        speaker_id=second_character.id,
    )

    assert updated.speaker_id == second_character.id
    assert updated.kind == DialogueType.Dialogue
    assert engine.get_story_dialogue(
        created.id
    ).speaker_id == second_character.id


def test_update_story_dialogue_change_kind(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="안녕!",
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    # Dialogue -> Narration
    updated = engine.update_story_dialogue(
        created.id,
        kind=DialogueType.Narration,
        speaker_id=None,
    )

    assert updated.kind == DialogueType.Narration
    assert updated.speaker_id is None

    # Narration -> Dialogue
    updated = engine.update_story_dialogue(
        created.id,
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    assert updated.kind == DialogueType.Dialogue
    assert updated.speaker_id == character.id

    assert engine.get_story_dialogue(created.id) == updated


def test_update_story_dialogue_without_changes(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(engine, turn.id)

    updated = engine.update_story_dialogue(created.id)

    assert updated.model_dump() == created.model_dump()


@pytest.mark.parametrize(
    ("changes", "expected_exception"),
    [
        ({"content": None}, InvalidOperationError),
        ({"position": None}, InvalidOperationError),
        ({"kind": None}, InvalidOperationError),
        ({"position": -1}, ValidationError),
        ({"kind": "InvalidType"}, ValidationError),
        ({"story_turn_id": 999}, ValidationError),
        ({"unknown_field": "value"}, ValidationError),
    ],
)
def test_update_story_dialogue_invalid_data(
    engine,
    changes,
    expected_exception,
):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(engine, turn.id)

    with pytest.raises(expected_exception):
        engine.update_story_dialogue(
            created.id,
            **changes,
        )

    assert engine.get_story_dialogue(created.id) == created


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": DialogueType.Dialogue},
        {"speaker_id": 999999},
    ],
)
def test_update_narration_invalid_speaker_state(
    engine,
    changes,
):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    created = create_sample_dialogue(engine, turn.id)

    with pytest.raises(InvalidOperationError):
        engine.update_story_dialogue(
            created.id,
            **changes,
        )

    assert engine.get_story_dialogue(created.id) == created


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": DialogueType.Narration},
        {"speaker_id": None},
    ],
)
def test_update_dialogue_invalid_speaker_state(
    engine,
    changes,
):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    with pytest.raises(InvalidOperationError):
        engine.update_story_dialogue(
            created.id,
            **changes,
        )

    assert engine.get_story_dialogue(created.id) == created


def test_update_story_dialogue_missing_speaker(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        engine.update_story_dialogue(
            created.id,
            speaker_id=999999,
        )

    assert exc_info.value.resource == "SessionCharacter"
    assert engine.get_story_dialogue(created.id) == created


def test_update_story_dialogue_other_session_speaker(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    turn = create_sample_turn(engine, first_session.id)

    first_character = create_sample_character(
        engine, first_session.id
    )
    other_character = create_sample_character(
        engine, second_session.id
    )

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        kind=DialogueType.Dialogue,
        speaker_id=first_character.id,
    )

    with pytest.raises(InvalidOperationError):
        engine.update_story_dialogue(
            created.id,
            speaker_id=other_character.id,
        )

    assert engine.get_story_dialogue(
        created.id
    ).speaker_id == first_character.id


def test_update_story_dialogue_duplicate_position(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine, turn.id, "첫 번째", position=0
    )
    second = create_sample_dialogue(
        engine, turn.id, "두 번째", position=1
    )

    with pytest.raises(IntegrityError):
        engine.update_story_dialogue(
            second.id,
            position=0,
        )

    assert engine.get_story_dialogue(first.id).position == 0
    assert engine.get_story_dialogue(second.id).position == 1


# DELETE

def test_delete_story_dialogue(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine, turn.id, "첫 번째 문장", position=0
    )
    second = create_sample_dialogue(
        engine, turn.id, "두 번째 문장", position=1
    )

    engine.delete_story_dialogue(first.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_story_dialogue(first.id)

    assert engine.get_story_dialogue(second.id).id == second.id

    results = engine.list_story_dialogues_for_turn(turn.id)
    assert [item.id for item in results] == [second.id]

    # Deleting a dialogue must not delete its StoryTurn.
    assert engine.get_story_turn(turn.id).id == turn.id


def test_delete_story_dialogue_preserves_character(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    created = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    engine.delete_story_dialogue(created.id)

    assert engine.get_session_character(
        character.id
    ).id == character.id

    assert engine.get_story_turn(turn.id).story_dialogues == []


def test_delete_story_turn_cascades_story_dialogues(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)

    first = create_sample_dialogue(
        engine, turn.id, "첫 번째", position=0
    )
    second = create_sample_dialogue(
        engine, turn.id, "두 번째", position=1
    )

    engine.delete_story_turn(turn.id)

    for dialogue in [first, second]:
        with pytest.raises(ResourceNotFoundError):
            engine.get_story_dialogue(dialogue.id)

    assert engine.list_story_dialogues_for_turn(turn.id) == []


def test_delete_session_cascades_story_dialogues(engine):
    narrative = create_sample_session(engine)
    turn = create_sample_turn(engine, narrative.id)
    character = create_sample_character(engine, narrative.id)

    narration = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        position=0,
    )
    dialogue = create_sample_dialogue(
        engine,
        story_turn_id=turn.id,
        content="누구냐!",
        position=1,
        kind=DialogueType.Dialogue,
        speaker_id=character.id,
    )

    engine.delete_session_narrative(narrative.id)

    for item in [narration, dialogue]:
        with pytest.raises(ResourceNotFoundError):
            engine.get_story_dialogue(item.id)

    assert (
        engine.list_story_dialogues_for_session_narrative(
            narrative.id
        ) == []
    )


# NOT FOUND

@pytest.mark.parametrize(
    "operation",
    ["get", "update", "delete"],
)
def test_story_dialogue_not_found(engine, operation):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        if operation == "get":
            engine.get_story_dialogue(nonexistent_id)
        elif operation == "update":
            engine.update_story_dialogue(
                nonexistent_id,
                content="Updated",
            )
        else:
            engine.delete_story_dialogue(nonexistent_id)

    assert exc_info.value.resource == "StoryDialogue"
    assert exc_info.value.resource_id == nonexistent_id


# PERSISTENCE

def test_story_dialogue_persistence(tmp_path):
    db_path = str(tmp_path / "story_dialogue_persistence.db")

    first_engine = NarrativeEngine(db_path)

    try:
        first_engine.initialize()

        narrative = create_sample_session(first_engine)
        turn = create_sample_turn(
            first_engine,
            narrative.id,
        )
        character = create_sample_character(
            first_engine,
            narrative.id,
        )

        created = create_sample_dialogue(
            first_engine,
            story_turn_id=turn.id,
            content="여기가 어디지?",
            position=0,
            kind=DialogueType.Dialogue,
            speaker_id=character.id,
        )

        dialogue_id = created.id
        turn_id = turn.id
        narrative_id = narrative.id
        character_id = character.id

    finally:
        first_engine.close()

    second_engine = NarrativeEngine(db_path)

    try:
        second_engine.initialize()

        retrieved = second_engine.get_story_dialogue(
            dialogue_id
        )

        assert retrieved.id == dialogue_id
        assert retrieved.story_turn_id == turn_id
        assert retrieved.content == "여기가 어디지?"
        assert retrieved.position == 0
        assert retrieved.kind == DialogueType.Dialogue
        assert retrieved.speaker_id == character_id

        turn_results = (
            second_engine.list_story_dialogues_for_turn(
                turn_id
            )
        )
        session_results = (
            second_engine.list_story_dialogues_for_session_narrative(
                narrative_id
            )
        )

        assert [item.id for item in turn_results] == [
            dialogue_id
        ]
        assert [item.id for item in session_results] == [
            dialogue_id
        ]

    finally:
        second_engine.close()
