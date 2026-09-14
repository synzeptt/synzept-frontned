"""
Tool interface and base class.

All tools must implement the BaseTool interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import time
import logging

from app.agent.models import (
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
    ToolExecutionResult,
)

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all agent tools."""

    def __init__(self):
        self._definition: Optional[ToolDefinition] = None

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        if self._definition is None:
            self._definition = self.get_definition()
        return self._definition

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """
        Return the tool definition (name, description, schema, etc.).
        
        This must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters: Input parameters matching the input_schema
            
        Returns:
            Output dict matching the output_schema
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If execution fails
        """
        pass

    async def execute_with_validation(
        self,
        step_id: str,
        parameters: dict[str, Any],
    ) -> ToolExecutionResult:
        """
        Execute the tool with validation and error handling.
        
        Args:
            step_id: ID of the execution step
            parameters: Input parameters
            
        Returns:
            ToolExecutionResult with success/failure info
        """
        try:
            # Validate input
            self._validate_input(parameters)
            
            # Execute
            start_time = time.time()
            output = await self.execute(parameters)
            execution_time = time.time() - start_time
            
            # Validate output
            self._validate_output(output)
            
            return ToolExecutionResult(
                tool_name=self.definition.name,
                step_id=step_id,
                success=True,
                output=output,
                execution_time_seconds=execution_time,
            )
            
        except ValueError as e:
            logger.error(f"Invalid input for {self.definition.name}: {str(e)}")
            return ToolExecutionResult(
                tool_name=self.definition.name,
                step_id=step_id,
                success=False,
                error=f"Invalid input: {str(e)}",
                error_details=str(e),
            )

        except Exception as e:
            logger.error(
                f"Execution error in {self.definition.name}: {str(e)}",
                exc_info=True
            )
            return ToolExecutionResult(
                tool_name=self.definition.name,
                step_id=step_id,
                success=False,
                error=f"Execution failed: {type(e).__name__}",
                error_details=str(e),
            )

    async def execute_with_context(
        self,
        step_id: str,
        parameters: dict[str, Any],
        execution_context: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Execute with trusted runtime context when a tool needs authorization."""
        return await self.execute_with_validation(step_id=step_id, parameters=parameters)

    def _validate_input(self, parameters: dict[str, Any]) -> None:
        """Validate input parameters against schema."""
        schema = self.definition.input_schema
        
        # Check required fields
        for required_field in schema.required:
            if required_field not in parameters:
                raise ValueError(f"Missing required parameter: {required_field}")
        
        # Could add more schema validation here (type checking, etc.)

    def _validate_output(self, output: dict[str, Any]) -> None:
        """Validate output against output schema."""
        # Basic validation: output should be a dict
        if not isinstance(output, dict):
            raise ValueError(f"Tool output must be a dict, got {type(output)}")
