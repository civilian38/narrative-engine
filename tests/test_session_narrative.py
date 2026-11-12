"""Session Narrative 통합 테스트.

기존 tests/conftest.py의 engine fixture(임시 SQLite DB + 마이그레이션)를 사용한다.
실행: uv run python -m pytest tests/test_session_narrative.py -v
"""

import pytest
from pydantic import ValidationError

from narrative_engine.engine import NarrativeEngine
from narrative_engine.domain.models import SessionCharacter
from narrative_engine.domain.schemas.session_character import SessionCharacterList
from narrative_engine.domain.schemas.session_narrative import (
    SessionNarrativeCreate,
    SessionNarrativeList,
    SessionNarrativeRetrieve,
)
from narrative_engine.exceptions import ResourceNotFoundError


# 테스트 데이터 생성 헬퍼
def create_sample_template(engine, name="Alien Invasion"):
    return engine.create_narrative_template(
        name=name,
        world_description="외계인이 침략한 지구",
        initial_situation="Sarah는 폐허에서 깨어났다.",
        template_description="외계인 침공 시나리오",
    )


def create_sample_character(engine, narrative_template_id, name="Sarah"):
    return engine.create_character_template(
        narrative_template_id=narrative_template_id,
        name=name,
        background_description=f"{name}는 외계인 침공의 생존자",
        initial_status="폐허에서 깨어난 상태",
    )


# CREATE: 제목을 생략하면 템플릿 이름을 사용하고 세계관/상황을 복사한다.
def test_create_session_narrative(engine):
    template = create_sample_template(engine)

    created = engine.create_session_narrative_template(template.id)

    assert isinstance(created, SessionNarrativeRetrieve)
    assert isinstance(created.id, int)
    assert created.id > 0
    assert created.narrative_template_id == template.id
    assert created.title == template.name
    assert created.world_description == template.world_description
    assert created.situation == template.initial_situation
    assert created.session_characters == []


# CREATE: 사용자 지정 제목은 원본 템플릿 이름을 변경하지 않는다.
def test_create_session_narrative_with_custom_title(engine):
    template = create_sample_template(engine)

    created = engine.create_session_narrative_template(
        narrative_template_id=template.id,
        title="첫 번째 생존 기록",
    )

    assert created.title == "첫 번째 생존 기록"
    assert created.narrative_template_id == template.id
    assert engine.get_narrative_template(template.id).name == "Alien Invasion"


# CREATE: 캐릭터 템플릿들이 독립적인 세션 캐릭터로 복제된다.
def test_create_session_narrative_copies_characters(engine):
    template = create_sample_template(engine)
    sarah = create_sample_character(engine, template.id, "Sarah")
    john = create_sample_character(engine, template.id, "John")

    created = engine.create_session_narrative_template(template.id)
    characters = {character.name: character for character in created.session_characters}

    assert len(characters) == 2
    assert set(characters) == {"Sarah", "John"}
    assert all(
        isinstance(character, SessionCharacterList)
        for character in characters.values()
    )
    assert characters["Sarah"].background_description == sarah.background_description
    assert characters["John"].background_description == john.background_description

    # SessionCharacterList에는 status 필드가 없으므로 DB 모델로 검증한다.
    with engine.database.session() as session:
        for character in characters.values():
            saved = session.get(SessionCharacter, character.id)
            assert saved is not None
            assert saved.session_narrative_id == created.id
            assert saved.status == "폐허에서 깨어난 상태"


# CREATE: 세션은 템플릿의 스냅샷이며 이후 템플릿 수정의 영향을 받지 않는다.
def test_session_narrative_is_independent_snapshot(engine):
    template = create_sample_template(engine)
    character = create_sample_character(engine, template.id)
    first = engine.create_session_narrative_template(template.id)

    engine.update_narrative_template(
        template.id,
        world_description="새롭게 변화한 지구",
        initial_situation="새로운 시작",
    )
    engine.update_character_template(
        character.id,
        name="Updated Sarah",
        initial_status="안전한 기지에서 대기 중",
    )

    second = engine.create_session_narrative_template(template.id)
    first_after_update = engine.get_session_narrative(first.id)

    assert first_after_update.world_description == "외계인이 침략한 지구"
    assert first_after_update.situation == "Sarah는 폐허에서 깨어났다."
    assert [c.name for c in first_after_update.session_characters] == ["Sarah"]
    assert second.world_description == "새롭게 변화한 지구"
    assert second.situation == "새로운 시작"
    assert [c.name for c in second.session_characters] == ["Updated Sarah"]

    with engine.database.session() as session:
        first_character = session.get(
            SessionCharacter, first_after_update.session_characters[0].id
        )
        second_character = session.get(
            SessionCharacter, second.session_characters[0].id
        )
        assert first_character.status == "폐허에서 깨어난 상태"
        assert second_character.status == "안전한 기지에서 대기 중"


# CREATE: 존재하지 않는 템플릿은 현재 서비스 구현대로 ValueError를 발생시킨다.
def test_create_session_narrative_with_missing_template(engine):
    with pytest.raises(ValueError, match="NarrativeTemplate 999999 not found"):
        engine.create_session_narrative_template(999999)


# CREATE SCHEMA: 선언된 제목 길이 제약을 검증한다.
@pytest.mark.parametrize("invalid_title", ["", "A" * 101])
def test_session_narrative_create_schema_invalid_title(invalid_title):
    with pytest.raises(ValidationError):
        SessionNarrativeCreate(
            narrative_template_id=1,
            title=invalid_title,
            world_description="세계관",
            situation="현재 상황",
        )


# READ
def test_get_session_narrative(engine):
    template = create_sample_template(engine)
    create_sample_character(engine, template.id)
    created = engine.create_session_narrative_template(template.id, title="Session 1")

    retrieved = engine.get_session_narrative(created.id)

    assert isinstance(retrieved, SessionNarrativeRetrieve)
    assert retrieved.id == created.id
    assert retrieved.title == "Session 1"
    assert retrieved.world_description == template.world_description
    assert retrieved.situation == template.initial_situation
    assert retrieved.narrative_template_id == template.id
    assert len(retrieved.session_characters) == 1
    assert retrieved.session_characters[0].name == "Sarah"


# LIST: 생성 순서대로 조회되며 각 항목은 목록용 스키마를 따른다.
def test_list_session_narratives(engine):
    template = create_sample_template(engine)
    first = engine.create_session_narrative_template(template.id, title="Session A")
    second = engine.create_session_narrative_template(template.id, title="Session B")
    third = engine.create_session_narrative_template(template.id, title="Session C")

    sessions = engine.get_list_session_narratives()

    assert all(isinstance(item, SessionNarrativeList) for item in sessions)
    assert [item.id for item in sessions] == [first.id, second.id, third.id]
    assert [item.title for item in sessions] == ["Session A", "Session B", "Session C"]
    assert all(item.narrative_template_id == template.id for item in sessions)


# LIST SCHEMA
def test_list_session_narrative_fields(engine):
    template = create_sample_template(engine)
    engine.create_session_narrative_template(template.id)

    session_narrative = engine.get_list_session_narratives()[0]

    assert set(session_narrative.model_dump()) == {
        "id", "title", "narrative_template_id"
    }


# SEARCH: 제목 부분 검색 + 앞뒤 공백 제거
def test_search_session_narratives(engine):
    template = create_sample_template(engine)
    for title in ["Alien Rescue", "Alien Invasion", "Medieval Quest"]:
        engine.create_session_narrative_template(template.id, title=title)

    results = engine.get_list_session_narratives(search_term="  Alien  ")

    assert {item.title for item in results} == {"Alien Rescue", "Alien Invasion"}


# SEARCH: 검색어가 비어 있으면 모든 세션을 반환한다.
@pytest.mark.parametrize("search_term", [None, "", "   "])
def test_search_session_narratives_with_empty_term(engine, search_term):
    template = create_sample_template(engine)
    engine.create_session_narrative_template(template.id, title="Session A")
    engine.create_session_narrative_template(template.id, title="Session B")

    assert len(engine.get_list_session_narratives(search_term)) == 2


# UPDATE: 일부 필드만 수정하고 실제 DB에 저장되는지 검증한다.
def test_update_session_narrative(engine):
    template = create_sample_template(engine)
    created = engine.create_session_narrative_template(template.id)

    updated = engine.update_session_narrative(
        created.id,
        title="Updated Session",
        situation="기지에서 새로운 동료를 만났다.",
    )

    assert isinstance(updated, SessionNarrativeRetrieve)
    assert updated.title == "Updated Session"
    assert updated.situation == "기지에서 새로운 동료를 만났다."
    assert updated.world_description == created.world_description
    assert updated.narrative_template_id == template.id

    retrieved = engine.get_session_narrative(created.id)
    assert retrieved.title == "Updated Session"
    assert retrieved.situation == "기지에서 새로운 동료를 만났다."


# UPDATE: world_description 단독 수정도 허용된다.
def test_update_session_narrative_world_description(engine):
    template = create_sample_template(engine)
    created = engine.create_session_narrative_template(template.id)

    updated = engine.update_session_narrative(
        created.id, world_description="황폐해진 우주 정거장"
    )

    assert updated.world_description == "황폐해진 우주 정거장"
    assert updated.situation == created.situation
    assert engine.get_session_narrative(created.id).world_description == (
        "황폐해진 우주 정거장"
    )


# UPDATE VALIDATION
@pytest.mark.parametrize(
    "update_data",
    [
        {"title": None},
        {"world_description": None},
        {"situation": None},
        {"title": ""},
        {"title": "A" * 101},
        {"unknown_field": "value"},
        {"narrative_template_id": 999999},
    ],
)
def test_update_session_narrative_invalid_data(engine, update_data):
    template = create_sample_template(engine)
    created = engine.create_session_narrative_template(template.id)

    with pytest.raises(ValidationError):
        engine.update_session_narrative(created.id, **update_data)

    # 유효하지 않은 업데이트는 기존 데이터를 변경하지 않아야 한다.
    assert engine.get_session_narrative(created.id).title == created.title


# UPDATE: 수정할 필드가 없으면 값이 그대로 유지된다.
def test_update_session_narrative_without_changes(engine):
    template = create_sample_template(engine)
    created = engine.create_session_narrative_template(template.id)

    updated = engine.update_session_narrative(created.id)

    assert updated.model_dump() == created.model_dump()


# DELETE
def test_delete_session_narrative(engine):
    template = create_sample_template(engine)
    created = engine.create_session_narrative_template(template.id)

    engine.delete_session_narrative(created.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_session_narrative(created.id)
    assert engine.get_list_session_narratives() == []


# NOT FOUND
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
def test_session_narrative_not_found(engine, operation):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError) as exc_info:
        if operation == "get":
            engine.get_session_narrative(nonexistent_id)
        elif operation == "update":
            engine.update_session_narrative(nonexistent_id, title="Updated")
        else:
            engine.delete_session_narrative(nonexistent_id)

    assert exc_info.value.resource == "SessionNarrative"
    assert exc_info.value.resource_id == nonexistent_id


# RELATIONSHIP: 원본 템플릿에서 관련 세션 목록을 조회할 수 있다.
def test_narrative_template_contains_session_narratives(engine):
    template = create_sample_template(engine)
    first = engine.create_session_narrative_template(template.id, title="First")
    second = engine.create_session_narrative_template(template.id, title="Second")

    retrieved = engine.get_narrative_template(template.id)

    assert {item.id for item in retrieved.session_narratives} == {
        first.id, second.id
    }
    assert {item.title for item in retrieved.session_narratives} == {
        "First", "Second"
    }


# SET NULL: 원본 템플릿을 삭제해도 세션과 복제 캐릭터는 유지된다.
def test_delete_template_keeps_session_narrative(engine):
    template = create_sample_template(engine)
    create_sample_character(engine, template.id)
    created = engine.create_session_narrative_template(template.id)
    session_character_id = created.session_characters[0].id

    engine.delete_narrative_template(template.id)

    retrieved = engine.get_session_narrative(created.id)
    assert retrieved.narrative_template_id is None
    assert retrieved.title == created.title
    assert retrieved.world_description == created.world_description
    assert retrieved.situation == created.situation
    assert [item.id for item in retrieved.session_characters] == [
        session_character_id
    ]
    assert engine.get_list_session_narratives()[0].narrative_template_id is None

    with engine.database.session() as session:
        assert session.get(SessionCharacter, session_character_id) is not None


# CASCADE DELETE: 세션 삭제 시 해당 세션 캐릭터들도 함께 삭제된다.
def test_delete_session_narrative_deletes_session_characters(engine):
    template = create_sample_template(engine)
    create_sample_character(engine, template.id, "Sarah")
    create_sample_character(engine, template.id, "John")
    created = engine.create_session_narrative_template(template.id)
    character_ids = [item.id for item in created.session_characters]

    engine.delete_session_narrative(created.id)

    with engine.database.session() as session:
        assert all(
            session.get(SessionCharacter, character_id) is None
            for character_id in character_ids
        )

    # 반대로 원본 NarrativeTemplate은 삭제되지 않아야 한다.
    assert engine.get_narrative_template(template.id).id == template.id


# PERSISTENCE: 엔진을 종료하고 같은 DB로 다시 연결해도 세션 정보가 남아 있다.
def test_session_narrative_persistence(tmp_path):
    db_path = str(tmp_path / "session_narrative_persistence.db")
    first_engine = NarrativeEngine(db_path)

    try:
        first_engine.initialize()
        template = create_sample_template(first_engine)
        create_sample_character(first_engine, template.id)
        created = first_engine.create_session_narrative_template(
            template.id, title="Saved Session"
        )
        session_narrative_id = created.id
        session_character_id = created.session_characters[0].id
    finally:
        first_engine.close()

    second_engine = NarrativeEngine(db_path)
    try:
        second_engine.initialize()
        retrieved = second_engine.get_session_narrative(session_narrative_id)

        assert retrieved.id == session_narrative_id
        assert retrieved.title == "Saved Session"
        assert retrieved.narrative_template_id == template.id
        assert retrieved.world_description == "외계인이 침략한 지구"
        assert retrieved.situation == "Sarah는 폐허에서 깨어났다."
        assert [item.id for item in retrieved.session_characters] == [
            session_character_id
        ]
    finally:
        second_engine.close()
