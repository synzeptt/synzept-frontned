"""
Tool Adapters - Bridge existing runners to the unified Tool interface.

Adapts existing StepExecutor runners (BrowserRunner, ResearchRunner, etc.)
to implement the unified Tool interface, allowing them to work
with the Tool System without modification.
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from app.tools.contract import (
    Tool,
    ToolDefinition,
    ToolInputSchema,
    ToolCategory,
    ToolResult,
)

if TYPE_CHECKING:
    from app.execution.engine import ExecutionContext, ExecutionSession, ExecutionState, ExecutionStep

logger = logging.getLogger(__name__)


class RunnerAsToolAdapter(Tool):
    """
    Adapts a StepExecutor runner to the Tool interface.
    
    This allows existing runners (BrowserRunner, ResearchRunner, etc.)
    to be used as Tools without modification to their implementation.
    """
    
    def __init__(
        self,
        runner_name: str,
        runner_instance: Any,
        category: ToolCategory,
        description: str = "",
        input_schema: Optional[ToolInputSchema] = None,
        timeout_seconds: int = 300,
        max_retries: int = 1,
    ):
        """
        Initialize the adapter.
        
        Args:
            runner_name: Name of the runner
            runner_instance: The StepExecutor runner instance
            category: Tool category
            description: Tool description
            input_schema: Input schema (auto-detected if not provided)
            timeout_seconds: Execution timeout
            max_retries: Maximum retry attempts
        """
        self.runner_name = runner_name
        self.runner_instance = runner_instance
        self._category = category
        self._description = description
        self._input_schema = input_schema or ToolInputSchema(
            parameters={"goal": "string", "metadata": "object"},
            required=["goal"],
            description="Input for " + runner_name,
        )
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
    
    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name=self.runner_name,
            description=self._description or f"{self.runner_name} execution",
            category=self._category,
            input_schema=self._input_schema,
            is_executable=True,
            requires_approval=False,
            timeout_seconds=self._timeout_seconds,
            max_retries=self._max_retries,
            supports_streaming=False,
        )
    
    async def execute(
        self,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
    ) -> ToolResult:
        """
        Execute the tool.
        
        Args:
            parameters: Input parameters
            context: Execution context
            user_id: User ID
            
        Returns:
            ToolResult with execution status and output
        """
        start_time = time.time()
        execution_id = None
        
        try:
            # Validate input
            is_valid, error_msg = await self.validate_input(parameters)
            if not is_valid:
                return ToolResult(
                    success=False,
                    tool_name=self.runner_name,
                    error=error_msg,
                    execution_time_seconds=time.time() - start_time,
                )
            
            # Extract parameters
            goal = parameters.get("goal", "")
            metadata = parameters.get("metadata", {})
            
            from app.execution.engine import ExecutionContext, ExecutionSession, ExecutionStep

            # Create execution session and step
            step = ExecutionStep(
                id=f"tool-step-{self.runner_name}",
                runner=self.runner_name,
                action=self.runner_name,
                metadata={**metadata, "goal": goal},
            )

            session = ExecutionSession(
                id=f"session-{self.runner_name}",
                goal=goal,
                steps=[step],
            )

            exec_context = ExecutionContext(
                session=session,
                metadata={"user_id": user_id, **(context or {})},
            )
            execution_id = session.id
            
            # Execute the runner with timeout
            try:
                result = await asyncio.wait_for(
                    self.runner_instance.execute(
                        step=step,
                        context=exec_context,
                        user_id=user_id,
                    ),
                    timeout=self._timeout_seconds,
                )
            except asyncio.TimeoutError:
                return ToolResult(
                    success=False,
                    tool_name=self.runner_name,
                    error=f"Execution timed out after {self._timeout_seconds} seconds",
                    execution_time_seconds=time.time() - start_time,
                    execution_id=execution_id,
                    retryable=True,
                )
            
            # Process result
            if result and isinstance(result, dict):
                success = result.get("status") == "completed"
                output = result.get("output") or result.get("result")
                error = result.get("error")
                
                return ToolResult(
                    success=success,
                    tool_name=self.runner_name,
                    output=output,
                    error=error,
                    execution_time_seconds=time.time() - start_time,
                    execution_id=execution_id,
                    retryable=not success,  # Runner errors are retryable by default
                    metadata=result.get("metadata", {}),
                )
            
            return ToolResult(
                success=False,
                tool_name=self.runner_name,
                error="Invalid runner response format",
                execution_time_seconds=time.time() - start_time,
                execution_id=execution_id,
            )
            
        except Exception as exc:
            logger.exception(
                f"Tool execution failed: {self.runner_name}",
                extra={
                    "tool": self.runner_name,
                    "error": str(exc),
                    "execution_id": execution_id,
                },
            )
            return ToolResult(
                success=False,
                tool_name=self.runner_name,
                error=str(exc),
                execution_time_seconds=time.time() - start_time,
                execution_id=execution_id,
                retryable=True,
            )
