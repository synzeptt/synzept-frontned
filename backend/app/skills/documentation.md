# Skill Framework

This package implements the Skill Framework that sits between the Planning Engine and the Worker Framework.

Key components:
- `Skill` base contract
- `SkillContext` and `SkillResult` models
- `SkillRegistry` for discovery and automatic registration
- `SkillManager` to orchestrate planning and worker invocations
- `PlannerAdapter` to translate planner output into executable Skills
- `MockSkill` for end-to-end validation

Skills must not call Workers directly; they should rely on `worker_manager` available in `SkillContext`.
