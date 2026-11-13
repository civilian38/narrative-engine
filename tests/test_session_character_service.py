import pytest
from pydantic import ValidationError
from sqlalchemy import delete, event, select, text
from sqlalchemy.exc import IntegrityError

from narrative_engine.domain.models import (
    SessionCharacter, SessionCharacterOpinion, SessionNarrative,
    StoryDialogue, StoryTurn, DialogueType,
)
from narrative_engine.exceptions import InvalidOperationError, ResourceNotFoundError


def narrative(engine):
    with engine.database.session() as session:
        item = SessionNarrative(title="Story", world_description="World", situation="Start")
        session.add(item)
        session.flush()
        return item.id


def character(engine, narrative_id, name="Alice"):
    return engine.create_session_character(narrative_id, name, "Background", "Ready")


def story(engine):
    narrative_id = narrative(engine)
    person = character(engine, narrative_id)
    with engine.database.session() as session:
        turn = StoryTurn(session_narrative_id=narrative_id, turn_index=0, user_input="Go")
        session.add(turn)
        session.flush()
        line = StoryDialogue(story_turn_id=turn.id, position=0,
                             kind=DialogueType.Dialogue, speaker_id=person.id, content="Hello")
        session.add(line)
        session.flush()
        return narrative_id, person.id, turn.id, line.id


def test_crud_and_filters(engine):
    first, second = narrative(engine), narrative(engine)
    a = character(engine, first)
    b = character(engine, second, "Bob")
    assert a.opinions_to_others == a.opinions_from_others == []
    assert engine.get_session_character(a.id) == a
    assert [x.id for x in engine.list_session_characters()] == [a.id, b.id]
    assert [x.id for x in engine.list_session_characters(" Alice ", first)] == [a.id]
    assert engine.list_session_characters("Bob", first) == []
    assert [x.id for x in engine.list_session_characters("  ", second)] == [b.id]
    changed = engine.update_session_character(a.id, status="Tired")
    assert changed.name == a.name and changed.status == "Tired"
    assert engine.update_session_character(a.id) == changed
    engine.delete_session_character(a.id)
    assert engine.get_session_character(b.id) == b
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character(a.id)


@pytest.mark.parametrize("operation", ["get", "update", "delete"])
def test_missing_character(engine, operation):
    with pytest.raises(ResourceNotFoundError) as error:
        getattr(engine.session_character_service, operation)(9999)
    assert error.value.resource == "SessionCharacter"
    assert error.value.resource_id == 9999


def test_missing_parent(engine):
    with pytest.raises(ResourceNotFoundError) as error:
        character(engine, 9999)
    assert error.value.resource == "SessionNarrative"
    assert engine.list_session_characters() == []


@pytest.mark.parametrize("changes", [
    {"name": None}, {"status": None}, {"background_description": None},
    {"name": ""}, {"name": "x" * 101}, {"session_narrative_id": 5},
])
def test_invalid_update_preserves_data(engine, changes):
    person = character(engine, narrative(engine))
    with pytest.raises(ValidationError):
        engine.update_session_character(person.id, **changes)
    assert engine.get_session_character(person.id) == person


@pytest.mark.parametrize("name", ["", "x" * 101, None])
def test_invalid_create(engine, name):
    with pytest.raises(ValidationError):
        character(engine, narrative(engine), name)
    assert engine.list_session_characters() == []


def test_opinions_are_serializable_after_session_close(engine):
    parent = narrative(engine)
    a, b = character(engine, parent), character(engine, parent, "Bob")
    with engine.database.session() as session:
        session.add_all([
            SessionCharacterOpinion(from_character_id=a.id, to_character_id=b.id, opinion="Trust"),
            SessionCharacterOpinion(from_character_id=b.id, to_character_id=a.id, opinion="Respect"),
        ])
    result = engine.get_session_character(a.id)
    assert result.opinions_to_others[0].opinion == "Trust"
    assert result.opinions_from_others[0].opinion == "Respect"
    assert "Trust" in engine.update_session_character(a.id, status="Busy").model_dump_json()
    engine.delete_session_character(a.id)
    assert engine.get_session_character(b.id).opinions_to_others == []
    assert engine.get_session_character(b.id).opinions_from_others == []


def test_referenced_delete_rejects_before_any_write(engine):
    parent, person, turn, line = story(engine)
    writes = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("DELETE", "UPDATE", "INSERT")):
            writes.append(statement)

    event.listen(engine.database.engine, "before_cursor_execute", capture)
    try:
        with pytest.raises(InvalidOperationError):
            engine.delete_session_character(person)
    finally:
        event.remove(engine.database.engine, "before_cursor_execute", capture)
    assert writes == []
    with engine.database.session() as session:
        dialogue = session.get(StoryDialogue, line)
        assert (dialogue.speaker_id, dialogue.content, dialogue.story_turn_id) == (person, "Hello", turn)
        assert session.get(SessionCharacter, person) is not None
        assert session.get(SessionNarrative, parent) is not None
    # The failed operation must not poison later transactions.
    assert engine.update_session_character(person, status="Ready").id == person


def test_unreferenced_delete_preserves_existing_story(engine):
    parent, speaker, turn, line = story(engine)
    other = character(engine, parent, "Other")
    engine.delete_session_character(other.id)
    with engine.database.session() as session:
        assert session.get(SessionCharacter, other.id) is None
        assert session.get(StoryDialogue, line).speaker_id == speaker
        assert session.get(StoryTurn, turn) is not None


@pytest.mark.parametrize("mode", ["service", "sql", "loaded_orm"])
def test_whole_narrative_delete_cascades(engine, mode):
    parent, person, turn, line = story(engine)
    survivor = story(engine)
    with engine.database.engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        ddl = connection.scalar(text("SELECT sql FROM sqlite_master WHERE name='story_dialogue'"))
        assert "NO ACTION" in ddl and "DEFERRABLE INITIALLY DEFERRED" in ddl
    if mode == "service":
        engine.delete_session_narrative(parent)
    else:
        with engine.database.session() as session:
            if mode == "sql":
                session.execute(delete(SessionNarrative).where(SessionNarrative.id == parent))
            else:
                item = session.get(SessionNarrative, parent)
                assert item.session_characters[0].dialogues
                assert item.story_turns[0].story_dialogues
                session.delete(item)
    with engine.database.session() as session:
        for model, removed, kept in zip(
            (SessionNarrative, SessionCharacter, StoryTurn, StoryDialogue),
            (parent, person, turn, line), survivor,
        ):
            assert session.get(model, removed) is None
            assert session.get(model, kept) is not None


def test_database_deferred_fk_still_protects_direct_delete(engine):
    _, person, _, line = story(engine)
    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            session.execute(delete(SessionCharacter).where(SessionCharacter.id == person))
            session.flush()  # NO ACTION is checked at commit, not here.
            assert session.get(SessionCharacter, person) is None
    with engine.database.session() as session:
        assert session.get(StoryDialogue, line).speaker_id == person
        assert session.get(SessionCharacter, person) is not None
