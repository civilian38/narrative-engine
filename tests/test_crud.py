import pytest

from narrative_engine.domain.models import DialogueType
from narrative_engine.exceptions import ResourceNotFoundError


def test_template_narrative_crud(engine):
    created = engine.create_template_narrative("Mystery", "A quiet town", "A body is found", "Noir")
    assert engine.get_template_narrative(created.id).name == "Mystery"
    assert [item.id for item in engine.list_template_narratives("Myst")] == [created.id]
    updated = engine.update_template_narrative(created.id, name="Cold Case")
    assert updated.name == "Cold Case"
    engine.delete_template_narrative(created.id)
    assert engine.list_template_narratives() == []


def test_template_character_crud_and_parent_relationship(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    character = engine.create_template_character(template.id, "Mira", "Scout", "Healthy")
    assert engine.get_template_character(character.id).template_narrative_id == template.id
    assert [c.id for c in engine.get_template_narrative(template.id).template_characters] == [character.id]
    assert [c.id for c in engine.list_template_characters("Mi")] == [character.id]
    assert engine.update_template_character(character.id, initial_status="Wounded").initial_status == "Wounded"
    engine.delete_template_character(character.id)
    assert engine.list_template_characters() == []


def test_session_narrative_snapshot_and_crud(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    engine.create_template_character(template.id, "Mira", "Scout", "Healthy")
    story = engine.create_session_narrative(template.id, title="My quest")
    assert story.title == "My quest"
    assert [c.name for c in story.session_characters] == ["Mira"]
    assert engine.get_session_narrative(story.id).template_narrative_id == template.id
    assert [s.id for s in engine.list_session_narratives("quest")] == [story.id]
    assert engine.update_session_narrative(story.id, situation="At the gate").situation == "At the gate"
    engine.delete_template_narrative(template.id)
    assert engine.get_session_narrative(story.id).template_narrative_id is None
    engine.delete_session_narrative(story.id)
    assert engine.list_session_narratives() == []


def test_session_character_opinion_crud(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    engine.create_template_character(template.id, "Alice", "A", "Well")
    engine.create_template_character(template.id, "Bob", "B", "Well")
    story = engine.create_session_narrative(template.id)
    alice, bob = story.session_characters
    assert [(c.name, c.background_description, c.status) for c in (alice, bob)] == [
        ("Alice", "A", "Well"),
        ("Bob", "B", "Well"),
    ]
    assert engine.get_session_character(alice.id).name == "Alice"
    assert [c.id for c in engine.list_session_characters(session_narrative_id=story.id)] == [alice.id, bob.id]
    assert engine.update_session_character(alice.id, status="Tired").status == "Tired"
    opinion = engine.create_session_character_opinion(story.id, alice.id, bob.id, "Trust")
    assert engine.get_session_character_opinion(opinion.id).opinion == "Trust"
    assert [o.id for o in engine.list_session_character_opinions(story.id, alice.id)] == [opinion.id]
    assert engine.update_session_character_opinion(opinion.id, opinion="Respect").opinion == "Respect"
    engine.delete_session_character_opinion(opinion.id)
    assert engine.list_session_character_opinions(story.id) == []
    engine.delete_session_character(alice.id)
    assert [c.id for c in engine.list_session_characters(session_narrative_id=story.id)] == [bob.id]


def test_directly_add_session_character_alongside_template_character(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    engine.create_template_character(template.id, "Mira", "Scout", "Healthy")
    story = engine.create_session_narrative(template.id)

    mira = story.session_characters[0]
    directly_added = engine.create_session_character(story.id, "Rook", "Guide", "Well")

    assert [c.id for c in engine.list_session_characters(session_narrative_id=story.id)] == [
        mira.id,
        directly_added.id,
    ]
    assert engine.get_session_character(directly_added.id).name == "Rook"


def test_turn_dialogue_crud_order_and_cascades(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    story = engine.create_session_narrative(template.id)
    character = engine.create_session_character(story.id, "Mira", "Scout", "Well")
    turn = engine.create_session_turn(story.id, "Enter the castle", [])
    assert turn.turn_index == 0
    narration = engine.create_session_dialogue(turn.id, "The gate opens.", 0, DialogueType.Narration)
    speech = engine.create_session_dialogue(turn.id, "Come in.", 1, DialogueType.Dialogue, character.id)
    assert [d.id for d in engine.get_session_turn(turn.id).session_dialogues] == [narration.id, speech.id]
    assert engine.get_session_dialogue(speech.id).speaker_id == character.id
    assert [d.id for d in engine.list_session_dialogues_for_session_narrative(story.id)] == [narration.id, speech.id]
    assert engine.update_session_dialogue(speech.id, content="Welcome.").content == "Welcome."
    turn2 = engine.create_session_turn(story.id, "Continue", [])
    assert turn2.turn_index == 1
    assert [t.id for t in engine.list_session_turns(session_narrative_id=story.id)] == [turn.id, turn2.id]
    engine.delete_session_turn(turn.id)
    assert engine.list_session_dialogues_for_turn(turn.id) == []
    assert engine.get_session_character(character.id).id == character.id
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_turn(turn.id)


def test_session_character_memory_crud_and_listing(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    story = engine.create_session_narrative(template.id)
    alice = engine.create_session_character(story.id, "Alice", "A", "Well")
    bob = engine.create_session_character(story.id, "Bob", "B", "Well")
    turn_one = engine.create_session_turn(story.id, "First event", [])
    turn_two = engine.create_session_turn(story.id, "Second event", [])

    alice_memory_two = engine.create_session_character_memory(
        alice.id, turn_two.id, "Alice remembers the second event"
    )
    alice_memory_one = engine.create_session_character_memory(
        alice.id, turn_one.id, "Alice remembers the first event"
    )
    bob_memory_one = engine.create_session_character_memory(
        bob.id, turn_one.id, "Bob remembers the first event"
    )

    assert engine.get_session_character_memory(alice_memory_one.id).memory == (
        "Alice remembers the first event"
    )
    assert [memory.id for memory in
            engine.list_session_character_memories_for_character(alice.id)] == [
        alice_memory_one.id,
        alice_memory_two.id,
    ]
    assert [memory.id for memory in
            engine.list_session_character_memories_for_turn(turn_one.id)] == [
        alice_memory_one.id,
        bob_memory_one.id,
    ]
    assert engine.update_session_character_memory(
        alice_memory_two.id, memory="Alice remembers more"
    ).memory == "Alice remembers more"

    engine.delete_session_character_memory(alice_memory_two.id)
    assert [memory.id for memory in
            engine.list_session_character_memories_for_character(alice.id)] == [
        alice_memory_one.id,
    ]
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character_memory(alice_memory_two.id)


def test_session_character_memory_cascades_with_turn(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    story = engine.create_session_narrative(template.id)
    character = engine.create_session_character(story.id, "Alice", "A", "Well")
    turn = engine.create_session_turn(story.id, "An event", [])
    memory = engine.create_session_character_memory(
        character.id, turn.id, "A remembered event"
    )

    engine.delete_session_turn(turn.id)

    assert engine.list_session_character_memories_for_character(character.id) == []
    with pytest.raises(ResourceNotFoundError):
        engine.get_session_character_memory(memory.id)


def test_empty_update_is_noop_and_missing_resources_raise(engine):
    template = engine.create_template_narrative("Quest", "World", "Start")
    assert engine.update_template_narrative(template.id).name == "Quest"
    with pytest.raises(
        ResourceNotFoundError,
        match="TemplateNarrative resource with ID 99999 was not found",
    ):
        engine.get_template_narrative(99999)
    with pytest.raises(ResourceNotFoundError):
        engine.delete_session_narrative(99999)
