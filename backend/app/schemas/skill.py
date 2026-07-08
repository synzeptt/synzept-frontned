from pydantic import BaseModel, Field


class SkillMetadataOut(BaseModel):
    name: str
    description: str
    category: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    requiredContext: list[str] = Field(default_factory=list)
    requiredPermissions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    completionCriteria: list[str] = Field(default_factory=list)


class SkillExecutionOut(BaseModel):
    skillName: str
    status: str
    plan: list[str] = Field(default_factory=list)
    result: str
