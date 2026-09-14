"""
Agent Execution API endpoints.

Exposes the agent orchestrator capabilities.
"""

from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.agent import AgentOrchestrator, get_tool_registry
from app.services.ai.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent")


class AgentRequestBody(BaseModel):
    """Request body for agent execution."""
    message: str
    context: dict = Field(default_factory=dict)
    project_id: UUID | None = None
    conversation_id: UUID | None = None


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""
    execution_id: str
    status: str
    request_message: str
    result: dict | None = None
    error: str | None = None


class ToolsListResponse(BaseModel):
    """Response listing available tools."""
    tools: list[dict]
    count: int


@router.post("/run", response_model=AgentExecutionResponse)
async def run_agent(
    body: AgentRequestBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Execute an agent request.
    
    The agent will:
    1. Understand the request
    2. Create an execution plan
    3. Execute the plan using available tools
    4. Verify and return results
    
    Args:
        body: Request with user message
        user: Authenticated user
        session: Database session
        
    Returns:
        AgentExecutionResponse with status and results
    """
    try:
        # Get AI service
        ai_service = AIService()
        
        # Keep the configured provider as the orchestrator primary; AIService owns fallback.
        provider = ai_service.registry.get(ai_service.registry.provider_order()[0])
        if not provider:
            raise HTTPException(
                status_code=503,
                detail="No AI provider available"
            )
        
        # Create orchestrator
        orchestrator = AgentOrchestrator(provider)
        
        # Execute request
        execution = await orchestrator.execute_request(
            user_id=str(user.id),
            request_message=body.message,
            context=body.context,
        )
        
        # Return response
        return AgentExecutionResponse(
            execution_id=execution.execution_id,
            status=execution.status.value,
            request_message=execution.request_message,
            result=execution.final_result,
            error=execution.error,
        )
        
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/tools", response_model=ToolsListResponse)
async def list_available_tools(user: User = Depends(get_current_user)):
    """
    List all available tools that the agent can use.
    
    Args:
        user: Authenticated user
        
    Returns:
        List of tool definitions
    """
    try:
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        tools_data = [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "input_schema": tool.input_schema.dict(),
            }
            for tool in tools
        ]
        
        return ToolsListResponse(
            tools=tools_data,
            count=len(tools_data),
        )
        
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tools: {str(e)}"
        )
