"""
Tool Executor - Orchestrates tool execution and chaining.

Handles:
- Tool execution with error handling
- Tool chaining (multiple tools in sequence)
- Execution history and activity recording
- Timeout and retry logic
- Result aggregation
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.tools.contract import Tool, ToolResult, ToolExecutionContext
from app.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Orchestrates tool execution with chaining support.
    
    Responsibilities:
    - Validate tool requests
    - Execute individual tools
    - Handle errors and retries
    - Support tool chaining
    - Record execution history
    - Return structured results
    """
    
    def __init__(self, user_id: Optional[UUID] = None, max_tool_steps: int = 10):
        """
        Initialize the executor.
        
        Args:
            user_id: User executing tools
            max_tool_steps: Maximum number of sequential tool calls
        """
        self.user_id = user_id
        self.registry = get_tool_registry()
        self.max_tool_steps = max_tool_steps
        self.execution_context = ToolExecutionContext(user_id=user_id)
        self.execution_context.max_tool_steps = max_tool_steps
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of the tool
            parameters: Input parameters
            timeout_seconds: Override timeout
            max_retries: Override max retries
            
        Returns:
            ToolResult with execution status and output
        """
        logger.info(f"Executing tool: {tool_name}", extra={"tool": tool_name})
        
        # Validate tool exists
        tool = self.registry.get(tool_name)
        if not tool:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=error_msg,
                retryable=False,
            )
        
        # Check if execution should continue
        if not self.execution_context.should_continue():
            error_msg = f"Max tool steps ({self.max_tool_steps}) exceeded"
            logger.warning(error_msg)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=error_msg,
                retryable=False,
            )
        
        # Validate input
        is_valid, error_msg = await tool.validate_input(parameters)
        if not is_valid:
            error_msg = error_msg or "Invalid input parameters"
            logger.warning(f"Input validation failed for {tool_name}: {error_msg}")
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=error_msg,
                retryable=False,
            )
        
        # Get execution parameters
        tool_def = tool.definition
        timeout = timeout_seconds or tool_def.timeout_seconds
        retries = max_retries if max_retries is not None else tool_def.max_retries
        
        # Try execution with retries
        last_error = None
        for attempt in range(retries + 1):
            try:
                logger.debug(
                    f"Tool execution attempt {attempt + 1}/{retries + 1}",
                    extra={"tool": tool_name, "attempt": attempt + 1},
                )
                
                # Execute the tool
                result = await tool.execute(
                    parameters=parameters,
                    context=self.execution_context.metadata,
                    user_id=self.user_id,
                )
                
                # Record result
                self.execution_context.add_result(tool_name, result)
                
                logger.info(
                    f"Tool execution completed: {tool_name}",
                    extra={
                        "tool": tool_name,
                        "success": result.success,
                        "execution_time": result.execution_time_seconds,
                    },
                )
                
                return result
                
            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {timeout} seconds"
                logger.warning(
                    last_error,
                    extra={"tool": tool_name, "timeout": timeout},
                )
                
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                result = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    error=last_error,
                    retryable=True,
                )
                self.execution_context.add_result(tool_name, result)
                return result
                
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    f"Tool execution failed: {tool_name}",
                    extra={"tool": tool_name, "error": last_error},
                    exc_info=True,
                )
                
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                result = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    error=last_error,
                    retryable=True,
                )
                self.execution_context.add_result(tool_name, result)
                return result
        
        # Should not reach here, but just in case
        result = ToolResult(
            success=False,
            tool_name=tool_name,
            error=last_error or "Unknown error",
            retryable=True,
        )
        self.execution_context.add_result(tool_name, result)
        return result
    
    def _resolve_reference(self, reference: str, previous_results: dict[str, ToolResult]) -> Any:
        """Resolve a reference like `research_tool.output.summary` from earlier tool results."""
        if not reference or not isinstance(reference, str):
            return None
        key = reference.strip()
        if not key:
            return None
        parts = [part.strip() for part in key.split(".") if part and part.strip()]
        if len(parts) < 2:
            return None
        tool_name = parts[0]
        result = previous_results.get(tool_name)
        if result is None:
            return None
        current: Any = result
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    def _resolve_parameter_value(self, value: Any, previous_results: dict[str, ToolResult]) -> Any:
        if isinstance(value, dict):
            return {k: self._resolve_parameter_value(v, previous_results) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_parameter_value(item, previous_results) for item in value]
        if not isinstance(value, str):
            return value

        matches = re.findall(r"\{\{\s*([^{}]+?)\s*\}\}", value)
        if not matches:
            return value
        resolved = value
        for match in matches:
            replacement = self._resolve_reference(match, previous_results)
            if replacement is None:
                continue
            resolved = resolved.replace(f"{{{{{match}}}}}", str(replacement))
        return resolved

    async def execute_tools_sequence(
        self,
        tool_sequence: list[dict[str, Any]],
    ) -> list[ToolResult]:
        """
        Execute a sequence of tools.
        
        Tool sequence format:
        [
            {"tool": "web_search", "parameters": {...}},
            {"tool": "pdf_tool", "parameters": {...}},
            ...
        ]
        
        Args:
            tool_sequence: List of tool calls to execute
            
        Returns:
            List of ToolResults in order
        """
        logger.info(
            f"Executing tool sequence with {len(tool_sequence)} tools",
            extra={"count": len(tool_sequence)},
        )
        
        results = []
        
        for step, tool_call in enumerate(tool_sequence, 1):
            if not self.execution_context.should_continue():
                logger.warning(
                    f"Tool sequence stopped at step {step}: max steps exceeded"
                )
                break
            
            tool_name = tool_call.get("tool")
            parameters = tool_call.get("parameters", {})
            resolved_parameters = self._resolve_parameter_value(parameters, self.execution_context.previous_results)
            
            if not tool_name:
                logger.error("Tool call missing tool name")
                results.append(
                    ToolResult(
                        success=False,
                        tool_name="unknown",
                        error="Tool call missing tool name",
                    )
                )
                continue
            
            # Execute the tool
            result = await self.execute_tool(tool_name, resolved_parameters)
            results.append(result)
            
            # Stop on critical failure
            if not result.success and not result.retryable:
                logger.warning(f"Tool sequence stopped at step {step}: non-retryable error")
                break
        
        logger.info(
            f"Tool sequence completed: {len(results)} tools executed",
            extra={
                "total": len(tool_sequence),
                "completed": len(results),
                "successful": sum(1 for r in results if r.success),
            },
        )
        
        return results
    
    def get_execution_summary(self) -> dict[str, Any]:
        """
        Get a summary of the execution.
        
        Returns:
            Summary dict with stats and history
        """
        results = self.execution_context.execution_history
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        
        return {
            "total_steps": len(results),
            "successful_steps": successful,
            "failed_steps": failed,
            "steps_executed": self.execution_context.current_step,
            "max_steps": self.execution_context.max_tool_steps,
            "can_continue": self.execution_context.should_continue(),
            "history": results,
            "previous_results": {
                name: result.to_dict()
                for name, result in self.execution_context.previous_results.items()
            },
        }
    
    def get_last_result(self) -> Optional[ToolResult]:
        """Get the result of the last executed tool."""
        return self.execution_context.get_last_result()
    
    def reset(self) -> None:
        """Reset execution context."""
        self.execution_context = ToolExecutionContext(user_id=self.user_id)
        self.execution_context.max_tool_steps = self.max_tool_steps
