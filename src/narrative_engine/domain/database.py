from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from narrative_engine.config import DEBUG_MODE


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=DEBUG_MODE
        )

        self.session_factory = sessionmaker(
            bind=self.engine
        )

    def create_session(self):
        return self.session_factory()

    def close(self):
        self.engine.dispose()