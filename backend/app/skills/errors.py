from typing import Optional


class SkillError(Exception):
    def __init__(self, message: str = "", *, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class PlanningFailure(SkillError):
    pass


class DependencyFailure(SkillError):
    pass


class WorkerOrchestrationFailure(SkillError):
    pass


class VerificationFailure(SkillError):
    pass


class ConnectorFailure(SkillError):
    pass


class ApprovalFailure(SkillError):
    pass
