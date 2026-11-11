from sqlalchemy import select

from narrative_engine.domain.models import NarrativeTemplate


def test_create_template(database):
    # Given: 새로운 템플릿 생성
    template = NarrativeTemplate(
        name="Alien Invasion",
        template_description="외계인 침공 시나리오",
        world_description="외계인이 지구를 침략했다.",
        initial_situation="Sarah는 폐허에서 깨어났다.",
    )

    # When: 데이터베이스에 저장
    with database.create_session() as session:
        session.add(template)
        session.commit()

        template_id = template.id

    # Then: 새로운 Session에서 조회
    with database.create_session() as session:
        stmt = select(NarrativeTemplate).where(
            NarrativeTemplate.id == template_id
        )

        saved_template = session.scalar(stmt)

        assert saved_template is not None
        assert saved_template.name == "Alien Invasion"
        assert saved_template.world_description == (
            "외계인이 지구를 침략했다."
        )


def test_nullable_description(database):
    template = NarrativeTemplate(
        name="Medieval Fantasy",
        template_description=None,
        world_description="마법이 존재하는 세계",
        initial_situation="용사가 마을에 도착했다.",
    )

    with database.create_session() as session:
        session.add(template)
        session.commit()

        template_id = template.id

    with database.create_session() as session:
        saved = session.get(
            NarrativeTemplate,
            template_id
        )

        assert saved is not None
        assert saved.template_description is None

import pytest

from sqlalchemy.exc import IntegrityError


def test_required_world_description(database):
    template = NarrativeTemplate(
        name="Invalid Template",
        template_description=None,
        world_description=None,
        initial_situation="시작 상황",
    )

    with database.create_session() as session:
        session.add(template)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

def test_update_and_delete_template(database):
    # 생성
    with database.create_session() as session:
        template = NarrativeTemplate(
            name="Original",
            template_description=None,
            world_description="기존 세계관",
            initial_situation="기존 시작 상황",
        )

        session.add(template)
        session.commit()

        template_id = template.id

    # 수정
    with database.create_session() as session:
        template = session.get(
            NarrativeTemplate,
            template_id
        )

        assert template is not None

        template.name = "Updated"
        session.commit()

    # 수정 결과 확인 및 삭제
    with database.create_session() as session:
        template = session.get(
            NarrativeTemplate,
            template_id
        )

        assert template is not None
        assert template.name == "Updated"

        session.delete(template)
        session.commit()

    # 삭제 확인
    with database.create_session() as session:
        template = session.get(
            NarrativeTemplate,
            template_id
        )

        assert template is None