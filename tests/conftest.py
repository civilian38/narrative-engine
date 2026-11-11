import pytest

from narrative_engine.domain.database import Database


@pytest.fixture
def database(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(str(db_path))
    db.migrate()

    yield db

    db.close()