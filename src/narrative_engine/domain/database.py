from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from narrative_engine.config import DEBUG_MODE


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=DEBUG_MODE,
        )

        self.session_factory = sessionmaker(
            bind=self.engine
        )

    def create_session(self):
        return self.session_factory()

    def session(self):
        return self.session_factory.begin()

    def migrate(self):
        package_dir = Path(__file__).resolve().parents[1]

        config = Config(
            str(package_dir / "alembic.ini")
        )

        config.set_main_option(
            "script_location",
            str(package_dir / "migrations")
        )

        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def close(self):
        self.engine.dispose()