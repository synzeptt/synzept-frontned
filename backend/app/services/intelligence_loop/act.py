from __future__ import annotations

from app.schemas.intelligence_loop import ActionApprovalIn, ActionRequestOut, RecommendationOut


class ActService:
    def create_action_requests(self, recommendations: list[RecommendationOut]) -> list[ActionRequestOut]:
        return [
            ActionRequestOut(
                id=f"act-{recommendation.id}",
                recommendationId=recommendation.id,
                title=f"Approve: {recommendation.action}",
                description=recommendation.why,
                permissionLevel="explicit_user_approval",
                status="pending_approval",
                approvalPrompt="Approve this action before Synzept changes anything or contacts anyone.",
                preview={
                    "action": recommendation.action,
                    "impact": str(recommendation.expectedImpact),
                    "effort": recommendation.effort,
                },
            )
            for recommendation in recommendations
            if recommendation.requiresApproval
        ]

    @staticmethod
    def record_approval(body: ActionApprovalIn) -> dict[str, str | bool | None]:
        return {
            "status": "approved" if body.approved else "rejected",
            "actionRequestId": body.actionRequestId,
            "executed": False,
            "note": body.note,
            "message": "Approval recorded. Mock mode never executes meaningful actions.",
        }
