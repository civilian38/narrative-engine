import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from narrative_engine.domain.models import (
    DialogueType,
    SessionCharacter,
    SessionCharacterOpinion,
    SessionDialogue,
    SessionNarrative,
    SessionTurn,
    TemplateCharacter,
)
from narrative_engine.exceptions import InvalidOperationError, ResourceNotFoundError


def story_data(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    story = engine.create_session_narrative(template.id)
    alice = engine.create_session_character(story.id, "Alice", "A", "Well")
    bob = engine.create_session_character(story.id, "Bob", "B", "Well")
    other = engine.create_session_narrative(template.id, title="Other")
    outsider = engine.create_session_character(other.id, "Eve", "E", "Well")
    turn = engine.create_session_turn(story.id, "Go", [])
    return template, story, alice, bob, outsider, turn


def test_sqlite_foreign_keys_are_enabled(engine):
    with engine.database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


@pytest.mark.parametrize("invalid", [
    lambda data: SessionTurn(session_narrative_id=data[1].id, turn_index=-1, user_input="x"),
    lambda data: SessionTurn(session_narrative_id=data[1].id, turn_index=0, user_input="duplicate"),
])
def test_turn_index_constraints(engine, invalid):
    data = story_data(engine)
    with pytest.raises(IntegrityError):
        with engine.database.session() as session:
            session.add(invalid(data))
            session.flush()


def test_dialogue_position_and_speaker_constraints(engine):
    data = story_data(engine)
    _, _, alice, _, _, turn = data
    invalid_rows = [
        SessionDialogue(session_turn_id=turn.id, position=-1, kind=DialogueType.Narration, speaker_id=None, content="x"),
        SessionDialogue(session_turn_id=turn.id, position=0, kind=DialogueType.Dialogue, speaker_id=None, content="x"),
        SessionDialogue(session_turn_id=turn.id, position=0, kind=DialogueType.Narration, speaker_id=alice.id, content="x"),
    ]
    for row in invalid_rows:
        with pytest.raises(IntegrityError):
            with engine.database.session() as session:
                session.add(row)
                session.flush()


def test_opinion_pair_constraints(engine):
    _, story, alice, bob, outsider, _ = story_data(engine)
    invalid_rows = [
        SessionCharacterOpinion(session_narrative_id=story.id, from_character_id=alice.id, to_character_id=alice.id, opinion="self"),
        SessionCharacterOpinion(session_narrative_id=story.id, from_character_id=alice.id, to_character_id=bob.id, opinion="duplicate"),
        SessionCharacterOpinion(session_narrative_id=story.id, from_character_id=alice.id, to_character_id=outsider.id, opinion="cross-session"),
    ]
    engine.create_session_character_opinion(story.id, alice.id, bob.id, "existing")
    for row in invalid_rows:
        with pytest.raises(IntegrityError):
            with engine.database.session() as session:
                session.add(row)
                session.flush()


def test_parent_deletes_apply_declared_cascade_and_set_null(engine):
    template, story, alice, bob, _, turn = story_data(engine)
    engine.create_session_character_opinion(story.id, alice.id, bob.id, "Trust")
    dialogue = engine.create_session_dialogue(turn.id, "Hi", 0, DialogueType.Dialogue, alice.id)

    engine.delete_template_narrative(template.id)
    assert engine.get_session_narrative(story.id).template_narrative_id is None
    with engine.database.session() as session:
        assert session.scalar(select(func.count()).select_from(TemplateCharacter)) == 0

    # Removing the complete narrative is permitted even when dialogue references a character.
    engine.delete_session_narrative(story.id)
    with engine.database.session() as session:
        assert session.get(SessionNarrative, story.id) is None
        assert session.get(SessionCharacter, alice.id) is None
        assert session.get(SessionTurn, turn.id) is None
        assert session.get(SessionDialogue, dialogue.id) is None
        assert session.scalar(select(func.count()).select_from(SessionCharacterOpinion)) == 0


def test_dialogue_restricts_character_delete_until_dialogue_is_removed(engine):
    _, story, alice, _, _, turn = story_data(engine)
    dialogue = engine.create_session_dialogue(turn.id, "Hi", 0, DialogueType.Dialogue, alice.id)
    with pytest.raises(InvalidOperationError):
        engine.delete_session_character(alice.id)
    assert engine.get_session_character(alice.id).id == alice.id
    engine.delete_session_dialogue(dialogue.id)
    engine.delete_session_character(alice.id)
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character(alice.id)


def test_character_without_dialogue_can_be_deleted(engine):
    _, story, alice, _, _, _ = story_data(engine)
    engine.delete_session_character(alice.id)
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character(alice.id)
