
"""SessionCharacterOpinion integration tests.

Uses the engine fixture from tests/conftest.py.

Run:
    uv run python -m pytest tests/test_session_character_opinion.py -v
"""

import pytest
from pydantic import ValidationError

from narrative_engine.engine import NarrativeEngine
from narrative_engine.domain.models import (
    SessionCharacterOpinion,
    SessionNarrative,
)
from narrative_engine.domain.schemas.session_character_opinion import (
    SessionCharacterOpinionCreate,
    SessionCharacterOpinionRetrieve,
    SessionCharacterOpinionList,
)
from narrative_engine.exceptions import (
    ResourceNotFoundError,
    InvalidOperationError,
)


# TEST DATA HELPERS

def create_sample_session(engine):
    with engine.database.session() as session:
        narrative = SessionNarrative(
            title="Alien Invasion",
            world_description="외계인이 침략한 지구",
            situation="Sarah는 폐허에서 깨어났다.",
        )
        session.add(narrative)
        session.flush()
        return narrative.id


def create_sample_character(
    engine,
    session_narrative_id,
    name="Sarah",
):
    return engine.create_session_character(
        session_narrative_id=session_narrative_id,
        name=name,
        background_description=f"{name}의 배경",
        status="건강함",
    )


def create_sample_opinion(
    engine,
    session_narrative_id,
    from_character_id,
    to_character_id,
    opinion="I trust this person.",
):
    return engine.create_session_character_opinion(
        session_narrative_id=session_narrative_id,
        from_character_id=from_character_id,
        to_character_id=to_character_id,
        opinion=opinion,
    )


def create_sample_characters(engine, session_narrative_id):
    alice = create_sample_character(
        engine, session_narrative_id, "Alice"
    )
    bob = create_sample_character(
        engine, session_narrative_id, "Bob"
    )
    charlie = create_sample_character(
        engine, session_narrative_id, "Charlie"
    )
    return alice, bob, charlie


# CREATE

def test_create_session_character_opinion(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    created = create_sample_opinion(
        engine,
        narrative_id,
        alice.id,
        bob.id,
        "Alice trusts Bob.",
    )

    assert isinstance(created, SessionCharacterOpinionRetrieve)
    assert created.id > 0
    assert created.session_narrative_id == narrative_id
    assert created.from_character_id == alice.id
    assert created.to_character_id == bob.id
    assert created.opinion == "Alice trusts Bob."


def test_create_opinions_in_both_directions(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    alice_opinion = create_sample_opinion(
        engine,
        narrative_id,
        alice.id,
        bob.id,
        "Alice trusts Bob.",
    )

    bob_opinion = create_sample_opinion(
        engine,
        narrative_id,
        bob.id,
        alice.id,
        "Bob distrusts Alice.",
    )

    assert alice_opinion.id != bob_opinion.id
    assert alice_opinion.from_character_id == alice.id
    assert alice_opinion.to_character_id == bob.id
    assert bob_opinion.from_character_id == bob.id
    assert bob_opinion.to_character_id == alice.id


def test_create_opinion_with_missing_session(engine):
    with pytest.raises(ResourceNotFoundError) as exc_info:
        create_sample_opinion(
            engine, 999999, 1, 2
        )

    assert exc_info.value.resource == "SessionNarrative"
    assert exc_info.value.resource_id == 999999


@pytest.mark.parametrize(
    "missing_character",
    ["from", "to"],
)
def test_create_opinion_with_missing_character(
    engine,
    missing_character,
):
    narrative_id = create_sample_session(engine)
    alice = create_sample_character(engine, narrative_id)

    if missing_character == "from":
        from_id = 999999
        to_id = alice.id
    else:
        from_id = alice.id
        to_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        create_sample_opinion(
            engine,
            narrative_id,
            from_id,
            to_id,
        )

    assert exc_info.value.resource == "SessionCharacter"
    assert exc_info.value.resource_id == 999999


def test_create_opinion_with_character_from_other_session(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    alice = create_sample_character(engine, first_session)
    bob = create_sample_character(engine, second_session, "Bob")

    with pytest.raises(InvalidOperationError):
        create_sample_opinion(
            engine,
            first_session,
            alice.id,
            bob.id,
        )

    assert engine.list_session_character_opinions(
        first_session
    ) == []


def test_create_opinion_about_self_rejected(engine):
    narrative_id = create_sample_session(engine)
    alice = create_sample_character(engine, narrative_id)

    with pytest.raises(InvalidOperationError):
        create_sample_opinion(
            engine,
            narrative_id,
            alice.id,
            alice.id,
        )

    assert engine.list_session_character_opinions(narrative_id) == []


def test_create_duplicate_directed_opinion_rejected(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine,
        narrative_id,
        alice.id,
        bob.id,
        "Trust",
    )

    with pytest.raises(InvalidOperationError):
        create_sample_opinion(
            engine,
            narrative_id,
            alice.id,
            bob.id,
            "Distrust",
        )

    results = engine.list_session_character_opinions(
        narrative_id
    )

    assert len(results) == 1
    assert results[0].id == first.id
    assert results[0].opinion == "Trust"


def test_create_invalid_opinion(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    with pytest.raises(ValidationError):
        create_sample_opinion(
            engine,
            narrative_id,
            alice.id,
            bob.id,
            None,
        )

    assert engine.list_session_character_opinions(narrative_id) == []

def test_create_opinion_schema_invalid_data():
    with pytest.raises(InvalidOperationError):
        SessionCharacterOpinionCreate(
            session_narrative_id=1,
            from_character_id=0,
            to_character_id=2,
            opinion="Trust",
        )


# READ

def test_get_session_character_opinion(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    created = create_sample_opinion(
        engine,
        narrative_id,
        alice.id,
        bob.id,
    )

    retrieved = engine.get_session_character_opinion(
        created.id
    )

    assert isinstance(retrieved, SessionCharacterOpinionRetrieve)
    assert retrieved.model_dump() == created.model_dump()


# LIST: WHOLE SESSION

def test_list_session_character_opinions(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id, "Trust"
    )
    second = create_sample_opinion(
        engine, narrative_id, bob.id, charlie.id, "Respect"
    )
    third = create_sample_opinion(
        engine, narrative_id, charlie.id, alice.id, "Fear"
    )

    results = engine.list_session_character_opinions(
        session_narrative_id=narrative_id
    )

    assert len(results) == 3
    assert all(
        isinstance(item, SessionCharacterOpinionList)
        for item in results
    )
    assert [item.id for item in results] == [
        first.id,
        second.id,
        third.id,
    ]


def test_list_session_character_opinion_fields(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )

    result = engine.list_session_character_opinions(
        narrative_id
    )[0]

    assert set(result.model_dump()) == {
        "id",
        "session_narrative_id",
        "from_character_id",
        "to_character_id",
        "opinion",
    }


# LIST: SPECIFIC CHARACTER

def test_list_opinions_for_character_as_from_character(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id, "Trust"
    )
    second = create_sample_opinion(
        engine, narrative_id, alice.id, charlie.id, "Respect"
    )

    create_sample_opinion(
        engine, narrative_id, bob.id, charlie.id, "Fear"
    )

    results = engine.list_session_character_opinions(
        session_narrative_id=narrative_id,
        character_id=alice.id,
    )

    assert [item.id for item in results] == [
        first.id,
        second.id,
    ]


def test_list_opinions_for_character_as_to_character(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id, "Trust"
    )
    second = create_sample_opinion(
        engine, narrative_id, charlie.id, bob.id, "Respect"
    )

    create_sample_opinion(
        engine, narrative_id, alice.id, charlie.id, "Fear"
    )

    results = engine.list_session_character_opinions(
        session_narrative_id=narrative_id,
        character_id=bob.id,
    )

    assert [item.id for item in results] == [
        first.id,
        second.id,
    ]


def test_list_opinions_for_character_in_both_directions(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id, "Trust"
    )
    second = create_sample_opinion(
        engine, narrative_id, bob.id, alice.id, "Respect"
    )

    create_sample_opinion(
        engine, narrative_id, bob.id, charlie.id, "Fear"
    )

    results = engine.list_session_character_opinions(
        session_narrative_id=narrative_id,
        character_id=alice.id,
    )

    assert [item.id for item in results] == [
        first.id,
        second.id,
    ]


def test_list_opinions_for_character_does_not_duplicate_results(
    engine,
):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    create_sample_opinion(
        engine, narrative_id, alice.id, bob.id, "Trust"
    )
    create_sample_opinion(
        engine, narrative_id, bob.id, alice.id, "Respect"
    )

    results = engine.list_session_character_opinions(
        narrative_id,
        character_id=alice.id,
    )

    assert len(results) == 2
    assert len({item.id for item in results}) == 2


def test_list_opinions_isolated_by_session(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    alice = create_sample_character(engine, first_session)
    bob = create_sample_character(engine, first_session, "Bob")

    charlie = create_sample_character(
        engine, second_session, "Charlie"
    )
    david = create_sample_character(
        engine, second_session, "David"
    )

    first = create_sample_opinion(
        engine, first_session, alice.id, bob.id
    )

    create_sample_opinion(
        engine, second_session, charlie.id, david.id
    )

    results = engine.list_session_character_opinions(
        first_session
    )

    assert [item.id for item in results] == [first.id]


def test_list_opinions_with_character_from_other_session(engine):
    first_session = create_sample_session(engine)
    second_session = create_sample_session(engine)

    alice = create_sample_character(engine, first_session)
    bob = create_sample_character(
        engine, second_session, "Bob"
    )

    with pytest.raises(InvalidOperationError):
        engine.list_session_character_opinions(
            session_narrative_id=first_session,
            character_id=bob.id,
        )


def test_list_opinions_with_missing_character(engine):
    narrative_id = create_sample_session(engine)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        engine.list_session_character_opinions(
            session_narrative_id=narrative_id,
            character_id=999999,
        )

    assert exc_info.value.resource == "SessionCharacter"
    assert exc_info.value.resource_id == 999999


def test_list_opinions_with_missing_session(engine):
    with pytest.raises(ResourceNotFoundError) as exc_info:
        engine.list_session_character_opinions(
            session_narrative_id=999999
        )

    assert exc_info.value.resource == "SessionNarrative"
    assert exc_info.value.resource_id == 999999

def test_list_empty_session_character_opinions(engine):
    narrative_id = create_sample_session(engine)
    alice = create_sample_character(engine, narrative_id)

    assert engine.list_session_character_opinions(narrative_id) == []

    assert engine.list_session_character_opinions(
        narrative_id,
        character_id=alice.id,
    ) == []

# UPDATE

def test_update_session_character_opinion(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    created = create_sample_opinion(
        engine,
        narrative_id,
        alice.id,
        bob.id,
        "Trust",
    )

    updated = engine.update_session_character_opinion(
        created.id,
        opinion="Complete trust",
    )

    assert isinstance(updated, SessionCharacterOpinionRetrieve)
    assert updated.id == created.id
    assert updated.session_narrative_id == narrative_id
    assert updated.from_character_id == alice.id
    assert updated.to_character_id == bob.id
    assert updated.opinion == "Complete trust"

    retrieved = engine.get_session_character_opinion(
        created.id
    )

    assert retrieved.model_dump() == updated.model_dump()


def test_update_session_character_opinion_without_changes(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    created = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )

    updated = engine.update_session_character_opinion(
        created.id
    )

    assert updated.model_dump() == created.model_dump()


@pytest.mark.parametrize(
    "changes",
    [
        {"opinion": None},
        {"opinion": ""},
        {"unknown_field": "value"},
        {"session_narrative_id": 999},
        {"from_character_id": 999},
        {"to_character_id": 999},
    ],
)
def test_update_session_character_opinion_invalid_data(
    engine,
    changes,
):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    created = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )

    expected_exception = (
        InvalidOperationError
        if changes == {"opinion": None}
        else ValidationError
    )

    with pytest.raises(expected_exception):
        engine.update_session_character_opinion(
            created.id,
            **changes,
        )


# DELETE

def test_delete_session_character_opinion(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )
    second = create_sample_opinion(
        engine, narrative_id, bob.id, charlie.id
    )

    engine.delete_session_character_opinion(first.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character_opinion(first.id)

    assert engine.get_session_character_opinion(
        second.id
    ).id == second.id

    results = engine.list_session_character_opinions(
        narrative_id
    )

    assert [item.id for item in results] == [second.id]


def test_delete_opinion_preserves_characters(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, _ = create_sample_characters(
        engine, narrative_id
    )

    opinion = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )

    engine.delete_session_character_opinion(opinion.id)

    assert engine.get_session_character(alice.id).id == alice.id
    assert engine.get_session_character(bob.id).id == bob.id


# NOT FOUND

@pytest.mark.parametrize(
    "operation",
    ["get", "update", "delete"],
)
def test_session_character_opinion_not_found(
    engine,
    operation,
):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        if operation == "get":
            engine.get_session_character_opinion(
                nonexistent_id
            )
        elif operation == "update":
            engine.update_session_character_opinion(
                nonexistent_id,
                opinion="Updated",
            )
        else:
            engine.delete_session_character_opinion(
                nonexistent_id
            )

    assert exc_info.value.resource == "SessionCharacterOpinion"
    assert exc_info.value.resource_id == nonexistent_id


# SESSION CASCADE

def test_delete_session_cascades_character_opinions(engine):
    narrative_id = create_sample_session(engine)
    alice, bob, charlie = create_sample_characters(
        engine, narrative_id
    )

    first = create_sample_opinion(
        engine, narrative_id, alice.id, bob.id
    )
    second = create_sample_opinion(
        engine, narrative_id, bob.id, charlie.id
    )

    engine.delete_session_narrative(narrative_id)

    for opinion in [first, second]:
        with pytest.raises(ResourceNotFoundError):
            engine.get_session_character_opinion(
                opinion.id
            )

    with pytest.raises(ResourceNotFoundError):
        engine.list_session_character_opinions(narrative_id)


# PERSISTENCE

def test_session_character_opinion_persistence(tmp_path):
    db_path = str(
        tmp_path / "session_character_opinion_persistence.db"
    )

    first_engine = NarrativeEngine(db_path)

    try:
        first_engine.initialize()

        narrative_id = create_sample_session(first_engine)
        alice, bob, _ = create_sample_characters(
            first_engine, narrative_id
        )

        created = create_sample_opinion(
            first_engine,
            narrative_id,
            alice.id,
            bob.id,
            "Alice trusts Bob.",
        )

        opinion_id = created.id
        alice_id = alice.id
        bob_id = bob.id

    finally:
        first_engine.close()

    second_engine = NarrativeEngine(db_path)

    try:
        second_engine.initialize()

        retrieved = second_engine.get_session_character_opinion(
            opinion_id
        )

        assert retrieved.id == opinion_id
        assert retrieved.from_character_id == alice_id
        assert retrieved.to_character_id == bob_id
        assert retrieved.opinion == "Alice trusts Bob."

        results = second_engine.list_session_character_opinions(
            session_narrative_id=narrative_id,
            character_id=alice_id,
        )

        assert [item.id for item in results] == [opinion_id]

    finally:
        second_engine.close()
