from fastapi import APIRouter, Query

from app.schemas.skill import SkillExecutionOut, SkillMetadataOut
from app.services.skill_registry import MockSkillRegistry

router = APIRouter(prefix="/api/internal/skills")


@router.get("", response_model=list[SkillMetadataOut])
async def list_skills(query: str = Query(default="")):
    registry = MockSkillRegistry()
    skills = registry.list()
    if query:
        query_lower = query.lower()
        skills = [skill for skill in skills if query_lower in skill.name.lower() or query_lower in skill.description.lower()]
    return [SkillMetadataOut(**skill.metadata()) for skill in skills]


@router.post("/execute", response_model=SkillExecutionOut)
async def execute_skill(skill_name: str, context: dict | None = None):
    registry = MockSkillRegistry()
    skill = registry.get(skill_name)
    if not skill:
        raise ValueError(f"Skill {skill_name} not found")
    return SkillExecutionOut(**skill.execute(context or {}))
