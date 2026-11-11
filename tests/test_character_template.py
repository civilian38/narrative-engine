
import pytest
from pydantic import ValidationError

from narrative_engine.engine import NarrativeEngine
from narrative_engine.exceptions import ResourceNotFoundError
from narrative_engine.domain.schemas.character_template import (
    CharacterTemplateRetrieve,
    CharacterTemplateList,
)


# 테스트 데이터 생성 헬퍼
def create_sample_narrative(engine):
    return engine.create_narrative_template(
        name="Alien Invasion",
        world_description="외계인이 침략한 지구",
        initial_situation="Sarah는 폐허에서 깨어났다.",
        template_description="외계인 침공 시나리오",
    )


def create_sample_character(
    engine,
    narrative_template_id,
    name="Sarah",
):
    return engine.create_character_template(
        narrative_template_id=narrative_template_id,
        name=name,
        background_description="외계인 침공에서 살아남은 생존자",
        initial_status="폐허에서 깨어난 상태",
    )


# CREATE
def test_create_character(engine):
    narrative = create_sample_narrative(engine)

    character = create_sample_character(
        engine,
        narrative.id,
    )

    assert isinstance(character, CharacterTemplateRetrieve)
    assert isinstance(character.id, int)
    assert character.id > 0
    assert character.name == "Sarah"
    assert character.background_description == (
        "외계인 침공에서 살아남은 생존자"
    )
    assert character.initial_status == "폐허에서 깨어난 상태"
    assert character.narrative_template_id == narrative.id


# READ
def test_get_character(engine):
    narrative = create_sample_narrative(engine)
    created = create_sample_character(engine, narrative.id)

    retrieved = engine.get_character_template(created.id)

    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.background_description == (
        created.background_description
    )
    assert retrieved.initial_status == created.initial_status
    assert retrieved.narrative_template_id == narrative.id


# LIST
def test_list_characters(engine):
    narrative = create_sample_narrative(engine)

    create_sample_character(engine, narrative.id, "Sarah")
    create_sample_character(engine, narrative.id, "John")
    create_sample_character(engine, narrative.id, "Alex")

    characters = engine.get_list_character_templates()

    assert len(characters) == 3
    assert all(
        isinstance(character, CharacterTemplateList)
        for character in characters
    )

    names = {character.name for character in characters}

    assert names == {"Sarah", "John", "Alex"}


# LIST SCHEMA
def test_list_character_fields(engine):
    narrative = create_sample_narrative(engine)
    create_sample_character(engine, narrative.id)

    characters = engine.get_list_character_templates()
    character = characters[0]

    assert set(character.model_dump().keys()) == {
        "id",
        "name",
        "background_description",
    }


# SEARCH
def test_search_characters(engine):
    narrative = create_sample_narrative(engine)

    create_sample_character(engine, narrative.id, "Sarah")
    create_sample_character(engine, narrative.id, "Sam")
    create_sample_character(engine, narrative.id, "John")

    results = engine.get_list_character_templates(
        search_term="Sa"
    )

    assert len(results) == 2

    names = {character.name for character in results}
    assert names == {"Sarah", "Sam"}


# UPDATE
def test_update_character(engine):
    narrative = create_sample_narrative(engine)
    created = create_sample_character(engine, narrative.id)

    updated = engine.update_character_template(
        created.id,
        name="Updated Sarah",
        initial_status="부상을 입은 상태",
    )

    assert updated.name == "Updated Sarah"
    assert updated.initial_status == "부상을 입은 상태"
    assert (
        updated.background_description
        == created.background_description
    )
    assert updated.narrative_template_id == narrative.id

    # DB에서 다시 조회하여 실제 저장 여부 확인
    retrieved = engine.get_character_template(created.id)

    assert retrieved.name == "Updated Sarah"
    assert retrieved.initial_status == "부상을 입은 상태"


# UPDATE VALIDATION
@pytest.mark.parametrize(
    "update_data",
    [
        {"name": None},
        {"background_description": None},
        {"initial_status": None},
        {"name": ""},
        {"name": "A" * 101},
        {"unknown_field": "value"},
    ],
)
def test_update_character_invalid_data(engine, update_data):
    narrative = create_sample_narrative(engine)
    created = create_sample_character(engine, narrative.id)

    with pytest.raises(ValidationError):
        engine.update_character_template(
            created.id,
            **update_data,
        )


# DELETE
def test_delete_character(engine):
    narrative = create_sample_narrative(engine)
    created = create_sample_character(engine, narrative.id)

    engine.delete_character_template(created.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_character_template(created.id)


# NOT FOUND
@pytest.mark.parametrize(
    "operation",
    ["get", "update", "delete"],
)
def test_character_not_found(engine, operation):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError):
        if operation == "get":
            engine.get_character_template(nonexistent_id)

        elif operation == "update":
            engine.update_character_template(
                nonexistent_id,
                name="Updated",
            )

        elif operation == "delete":
            engine.delete_character_template(nonexistent_id)


# RELATIONSHIP
def test_narrative_contains_characters(engine):
    narrative = create_sample_narrative(engine)

    first = create_sample_character(
        engine,
        narrative.id,
        "Sarah",
    )
    second = create_sample_character(
        engine,
        narrative.id,
        "John",
    )

    retrieved = engine.get_narrative_template(narrative.id)

    assert len(retrieved.character_templates) == 2

    character_ids = {
        character.id
        for character in retrieved.character_templates
    }

    assert character_ids == {first.id, second.id}

    assert all(
        isinstance(character, CharacterTemplateList)
        for character in retrieved.character_templates
    )


# CASCADE DELETE
def test_delete_narrative_deletes_characters(engine):
    narrative = create_sample_narrative(engine)

    first = create_sample_character(
        engine,
        narrative.id,
        "Sarah",
    )
    second = create_sample_character(
        engine,
        narrative.id,
        "John",
    )

    engine.delete_narrative_template(narrative.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_character_template(first.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_character_template(second.id)


# PERSISTENCE
def test_character_persistence(tmp_path):
    db_path = str(tmp_path / "character_persistence.db")

    first_engine = NarrativeEngine(db_path)

    try:
        first_engine.initialize()

        narrative = create_sample_narrative(first_engine)
        character = create_sample_character(
            first_engine,
            narrative.id,
        )

        character_id = character.id
        narrative_id = narrative.id

    finally:
        first_engine.close()

    # 새 Engine 인스턴스로 동일 DB를 다시 열기
    second_engine = NarrativeEngine(db_path)

    try:
        second_engine.initialize()

        retrieved = second_engine.get_character_template(
            character_id
        )

        assert retrieved.id == character_id
        assert retrieved.name == "Sarah"
        assert retrieved.narrative_template_id == narrative_id

    finally:
        second_engine.close()
