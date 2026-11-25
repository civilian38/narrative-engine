
import pytest

from narrative_engine.engine import NarrativeEngine


"""
uv run python -m pytest tests/ -v
"""


@pytest.fixture
def engine(tmp_path, monkeypatch):
    # Database and CRUD tests do not need to initialize the native Llama model.
    monkeypatch.setattr("narrative_engine.engine.Llama", lambda **kwargs: None)
    db_path = tmp_path / "test_narrative.db"

    narrative_engine = NarrativeEngine(
        db_path=str(db_path)
    )

    try:
        narrative_engine.initialize()
        yield narrative_engine
    finally:
        narrative_engine.close()

