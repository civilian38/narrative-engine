from narrative_engine.domain.database import Database


class NarrativeEngine:
    def __init__(
        self,
        db_path: str = "narrative.db",
    ):
        self.database = Database(db_path)

    def initialize(self):
        self.database.migrate()

    def close(self):
        self.database.close()