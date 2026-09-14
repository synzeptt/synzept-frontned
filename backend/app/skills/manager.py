from typing import Any, Dict, Optional, Type, List
import time

from .registry import default_registry
from .context import SkillContext
from .result import SkillResult, VerificationResult, SkillExecutionStatus, ExecutionMetrics
from .errors import WorkerOrchestrationFailure, VerificationFailure
from ..workers.result import WorkerResult, ExecutionStatus as WorkerExecutionStatus
from ..events import default_event_bus


class SkillManager:
    def __init__(self, registry=default_registry, dependencies: Dict[str, Any] = None):
        self.registry = registry
        self.dependencies = dependencies or {}

    def get_skill_class(self, capability: str) -> Type:
        cls = self.registry.get_skill_class(capability)
        if cls is None:
            raise KeyError(f"Skill not found for capability: {capability}")
        return cls

    def instantiate(self, skill_cls: Type, **overrides) -> object:
        deps = dict(self.dependencies)
        deps.update(overrides)
        return skill_cls(**deps)

    def run(self, skill_instance: Any, context: SkillContext) -> SkillResult:
        metrics = ExecutionMetrics()
        try:
            context.runtime_context["understanding"] = skill_instance.understand(context)
            default_event_bus.emit("skill.understood", {"execution_id": context.execution_id, "skill": skill_instance.identity})
            # planning
            planning = skill_instance.plan(context)
            # prepare
            skill_instance.prepare(context)
            # orchestrate workers according to planning
            worker_results: List[WorkerResult] = []
            for step in planning.planned_steps:
                capability = step.get("capability")
                inputs = step.get("inputs", {})
                candidate_capabilities = [capability]
                if capability:
                    candidate_capabilities.append(capability.split(".", 1)[0])
                last_error: Exception | None = None
                wr: WorkerResult | None = None
                for candidate in dict.fromkeys(candidate_capabilities):
                    try:
                        wr = context.worker_manager.run(candidate, context=HTTPCompatContext(context, inputs))
                        break
                    except Exception as exc:
                        last_error = exc
                        wr = None
                if wr is None:
                    wr = WorkerResult(status=WorkerExecutionStatus.FAILURE, message=str(last_error or "worker unavailable"), outputs={"error": str(last_error or "worker unavailable")})
                worker_results.append(wr)

            # Record worker failures but allow the skill to continue when it can produce a valid result from fallback state.
            failed_workers = [wr for wr in worker_results if getattr(wr, "status", None) == WorkerExecutionStatus.FAILURE]
            if failed_workers:
                context.runtime_context["worker_failures"] = [getattr(wr, "message", None) for wr in failed_workers]
                default_event_bus.emit("skill.worker_failed", {"execution_id": context.execution_id, "worker_results": worker_results})

            # execute the skill lifecycle step and merge its structured outputs
            execution_result = skill_instance.execute(context)
            if failed_workers:
                has_recovery_output = bool(
                    context.runtime_context.get("report")
                    or context.runtime_context.get("artifacts")
                    or execution_result.outputs.get("report")
                    or execution_result.outputs.get("artifacts")
                    or context.runtime_context.get("sources")
                )
                if not has_recovery_output:
                    metrics.finish()
                    return SkillResult(status=SkillExecutionStatus.FAILURE, outputs={"workers": [w.outputs for w in worker_results], **execution_result.outputs}, message="worker failure", metrics=metrics)
            if execution_result.status == SkillExecutionStatus.FAILURE:
                metrics.finish()
                default_event_bus.emit("skill.execution_failed", {"execution_id": context.execution_id, "skill": skill_instance.identity, "message": execution_result.message})
                return SkillResult(status=SkillExecutionStatus.FAILURE, outputs={"workers": [w.outputs for w in worker_results], **execution_result.outputs}, message=execution_result.message, metrics=metrics)

            # collect and verify
            verification = skill_instance.verify(context)
            metrics.finish()
            # build result
            status = SkillExecutionStatus.SUCCESS if verification.passed else SkillExecutionStatus.FAILURE
            outputs = {"workers": [w.outputs for w in worker_results], **execution_result.outputs}
            skill_result = SkillResult(status=status, outputs=outputs, message=verification.message, metrics=metrics)
            skill_result.outputs["artifacts"] = skill_instance.deliver(context, skill_result)
            context.runtime_context["learning_signal"] = skill_instance.learn(context, skill_result)
            default_event_bus.emit("skill.delivered", {"execution_id": context.execution_id, "skill": skill_instance.identity, "artifact_count": len(skill_result.outputs["artifacts"])})
            default_event_bus.emit("skill.learned", {"execution_id": context.execution_id, "skill": skill_instance.identity, "status": skill_result.status.value})
            return skill_result
        except Exception as e:
            metrics.finish()
            raise


# Small adapter to allow WorkerManager.run signature reuse: WorkerManager expects WorkerContext
class HTTPCompatContext:
    def __init__(self, skill_context: SkillContext, inputs: Dict[str, Any]):
        # create a minimal object with attributes used by WorkerManager/MockWorker
        from ..workers.context import WorkerContext

        # share runtime_context so workers can communicate via the shared dict
        self._wc = WorkerContext(
            execution_id=skill_context.execution_id,
            goal=skill_context.goal,
            inputs=inputs,
            runtime_context=skill_context.runtime_context,
            connectors=skill_context.connectors,
        )

    def __getattr__(self, item):
        return getattr(self._wc, item)
