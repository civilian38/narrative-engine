
import pytest

from narrative_engine.engine import NarrativeEngine
from narrative_engine.exceptions import ResourceNotFoundError


# 테스트 데이터 생성 헬퍼
def create_sample_template(engine, name="Alien Invasion"):
    return engine.create_narrative_template(
        name=name,
        world_description="외계인이 침략한 지구",
        initial_situation="Sarah는 폐허에서 깨어났다.",
        template_description="외계인 침공 시나리오",
    )


# CREATE
def test_create_template(engine):
    template = create_sample_template(engine)

    assert isinstance(template.id, int)
    assert template.id > 0
    assert template.name == "Alien Invasion"
    assert template.world_description == "외계인이 침략한 지구"


# READ
def test_get_template(engine):
    created = create_sample_template(engine)

    retrieved = engine.get_narrative_template(created.id)

    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert retrieved.initial_situation == created.initial_situation


# LIST
def test_list_templates(engine):
    create_sample_template(engine, "Alien Invasion")
    create_sample_template(engine, "Medieval Fantasy")
    create_sample_template(engine, "Alien Planet")

    templates = engine.get_list_narrative_templates()

    assert len(templates) == 3

    names = {template.name for template in templates}
    assert names == {
        "Alien Invasion",
        "Medieval Fantasy",
        "Alien Planet",
    }


# SEARCH
def test_search_templates(engine):
    create_sample_template(engine, "Alien Invasion")
    create_sample_template(engine, "Medieval Fantasy")
    create_sample_template(engine, "Alien Planet")

    results = engine.get_list_narrative_templates(
        search_term="Alien"
    )

    assert len(results) == 2
    assert all("Alien" in item.name for item in results)


# UPDATE
def test_update_template(engine):
    created = create_sample_template(engine)

    updated = engine.update_narrative_template(
        created.id,
        name="Updated Alien Invasion",
    )

    assert updated.name == "Updated Alien Invasion"
    assert updated.world_description == created.world_description
    assert updated.initial_situation == created.initial_situation

    # DB에서 다시 조회하여 실제 저장 여부 확인
    retrieved = engine.get_narrative_template(created.id)

    assert retrieved.name == "Updated Alien Invasion"


# DELETE
def test_delete_template(engine):
    created = create_sample_template(engine)

    engine.delete_narrative_template(created.id)

    with pytest.raises(ResourceNotFoundError):
        engine.get_narrative_template(created.id)


# NOT FOUND
@pytest.mark.parametrize(
    "operation",
    ["get", "update", "delete"],
)
def test_template_not_found(engine, operation):
    nonexistent_id = 999999

    with pytest.raises(ResourceNotFoundError):
        if operation == "get":
            engine.get_narrative_template(nonexistent_id)

        elif operation == "update":
            engine.update_narrative_template(
                nonexistent_id,
                name="Updated",
            )

        elif operation == "delete":
            engine.delete_narrative_template(nonexistent_id)


# PERSISTENCE
def test_template_persistence(tmp_path):
    db_path = str(tmp_path / "persistence.db")

    first_engine = NarrativeEngine(db_path)

    try:
        first_engine.initialize()
        created = create_sample_template(first_engine)
        template_id = created.id
    finally:
        first_engine.close()

    # 새 Engine 인스턴스로 동일 DB를 다시 열기
    second_engine = NarrativeEngine(db_path)

    try:
        second_engine.initialize()
        retrieved = second_engine.get_narrative_template(
            template_id
        )

        assert retrieved.name == "Alien Invasion"
        assert retrieved.id == template_id
    finally:
        second_engine.close()
