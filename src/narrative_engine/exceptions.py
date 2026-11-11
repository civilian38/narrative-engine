class NarrativeEngineError(Exception):
    """서사 엔진에서 발생하는 예외의 기본 클래스."""


class ResourceNotFoundError(NarrativeEngineError):
    def __init__(self, resource: str, resource_id: int):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(
            f"{resource} with id={resource_id} was not found"
        )


class InvalidOperationError(NarrativeEngineError):
    """도메인 규칙에 위반되는 작업."""


class PersistenceError(NarrativeEngineError):
    """데이터 저장 및 조회 중 발생한 오류."""