
import pytest

from narrative_engine.engine import NarrativeEngine


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test_narrative.db"

    narrative_engine = NarrativeEngine(
        db_path=str(db_path)
    )

    try:
        narrative_engine.initialize()
        yield narrative_engine
    finally:
        narrative_engine.close()
