"""
Agent Orchestrator - Core execution engine.

The orchestrator is responsible for:
1. Understanding user requests
2. Creating execution plans
3. Executing plans step by step
4. Handling errors and retries
5. Verifying results
6. Returning final results
"""

import logging
import json
import os
import re
from dataclasses import replace
from datetime import datetime
from typing import Awaitable, Callable, Optional, Any

from app.agent.models import (
    AgentPlan,
    AgentStep,
    AgentExecution,
    AgentStepExecution,
    ExecutionStatus,
    ToolExecutionResult,
    AgentStepInput,
)
from app.agent.registry import get_tool_registry
from app.agent.tool import BaseTool
from app.services.ai.base_provider import BaseAIProvider, AIMessage, AIRequest, AIResponse
from app.services.ai.ai_service import AIService
from app.services.ai.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Main orchestrator for agent execution.
    
    Handles the complete lifecycle of an agent request:
    - Plan creation
    - Step execution
    - Error handling
    - Verification
    - Result delivery
    """

    def __init__(self, ai_provider: BaseAIProvider | None):
        """
        Initialize the orchestrator.

        Args:
            ai_provider: Provider for AI completion (planning, reasoning). May be
            None when the environment does not have an LLM configured; the
            orchestrator still supports mocked or deferred execution paths.
        """
        self.ai_provider = ai_provider
        self.ai_service = AIService(ProviderRegistry(), primary_provider=ai_provider)
        self.tool_registry = get_tool_registry()

    async def execute_request(
        self,
        user_id: str,
        request_message: str,
        context: Optional[dict[str, Any]] = None,
        on_plan: Callable[[AgentPlan], Awaitable[None]] | None = None,
        on_status: Callable[[str, AgentExecution], Awaitable[None]] | None = None,
    ) -> AgentExecution:
        """
        Execute a user request end-to-end.
        
        Args:
            user_id: ID of the user making the request
            request_message: The user's request
            context: Optional context for execution
            
        Returns:
            AgentExecution with final result and status
        """
        execution = AgentExecution(
            user_id=user_id,
            request_message=request_message,
        )
        
        try:
            # Step 1: Create plan
            logger.info(f"Execution {execution.execution_id}: Planning")
            execution.status = ExecutionStatus.PLANNING
            planning_context = dict(context or {})
            planning_context.setdefault("user_id", user_id)
            plan = await self._create_plan(request_message, planning_context)
            execution.plan = plan
            
            # Step 2: Validate plan
            self._validate_plan(plan)
            if on_plan:
                await on_plan(plan)
            
            # Step 3: Execute steps
            logger.info(f"Execution {execution.execution_id}: Starting execution")
            execution.status = ExecutionStatus.RUNNING
            if on_status:
                await on_status(ExecutionStatus.RUNNING.value, execution)
            await self._execute_steps(execution, on_status=on_status)
            
            # Step 4: Verify results
            logger.info(f"Execution {execution.execution_id}: Verifying")
            execution.status = ExecutionStatus.VERIFYING
            if on_status:
                await on_status(ExecutionStatus.VERIFYING.value, execution)
            await self._verify_execution(execution)
            
            # Step 5: Mark complete
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            if on_status:
                await on_status(ExecutionStatus.COMPLETED.value, execution)
            
            logger.info(f"Execution {execution.execution_id}: Completed successfully")
            
        except Exception as e:
            logger.error(
                f"Execution {execution.execution_id}: Failed with exception: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Log the full details for debugging
            import traceback
            full_traceback = traceback.format_exc()
            logger.error(f"Full traceback:\n{full_traceback}")
            
            planning_failed = execution.status == ExecutionStatus.PLANNING
            execution.status = ExecutionStatus.FAILED
            execution.error = (
                "I couldn't plan that task correctly. Please try again."
                if planning_failed
                else str(e)
            )
            execution.completed_at = datetime.utcnow()
            if on_status:
                await on_status(ExecutionStatus.FAILED.value, execution)
        
        return execution

    async def _create_plan(
        self,
        request_message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentPlan:
        """
        Create an execution plan from the user request.
        
        Uses the AI provider to generate a structured plan.
        
        Args:
            request_message: The user's request
            context: Optional context
            
        Returns:
            AgentPlan with steps to execute
        """
        # Get available tools
        available_tools = self.tool_registry.list_tools()
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}; required input: "
            f"{', '.join(tool.input_schema.required) or 'none'}; parameters: "
            f"{', '.join(tool.input_schema.properties) or 'none'}"
            for tool in available_tools
        ])
        
        # Build prompt for planning
        system_prompt = f"""You are an AI agent orchestrator. Your job is to create execution plans.

Available tools:
{tools_description}

Tool names are exact identifiers from the list above. Only registered tool names
are valid; never invent alternative names such as search_web, browse_web,
create_pdf, write_file, or any other alias. Research requests MUST use the
research tool. PDF creation requests MUST use the pdf_generation tool.

For any user request, you must:
1. Understand the user's goal
2. Create a plan using the available tools
3. Return a JSON response with this exact structure:

{{
  "goal": "User's goal",
  "description": "Brief description of the plan",
  "steps": [
    {{
      "id": "step_1",
      "tool_name": "name of tool",
      "description": "What this step does",
      "input": {{
        "tool_name": "name of tool",
        "parameters": {{
          "param1": "value",
          ...
        }}
      }},
      "reason": "Why this step is needed",
      "depends_on": [],
      "retry_on_failure": true,
      "max_retries": 1
    }},
    ...
  ],
  "verification_requirements": {{}}
}}

Only return the JSON, no other text.
"""
        
        user_message = f"""User request: {request_message}

    Execution context: {context or {}}

Create an execution plan."""
        
        # Call AI to create plan
        messages = [
            AIMessage(role="system", content=system_prompt),
            AIMessage(role="user", content=user_message),
        ]
        request = AIRequest(
            messages=messages,
            temperature=0.3,  # Lower temp for deterministic planning
            response_mime_type="application/json",
            response_schema=self._plan_response_schema(),
        )

        response = await self._complete_plan_request(request)
        try:
            plan = self._parse_plan_response(response)
            self._validate_plan(plan)
        except (ValueError, TypeError) as exc:
            correction = AIMessage(
                role="user",
                content=(
                    f"Your previous response was invalid ({exc}). "
                    "Return one JSON object matching AgentPlan exactly: top-level "
                    "goal (string), description (string), steps (array), and "
                    "verification_requirements (object). Use only these registered "
                    f"tool definitions: {tools_description}. "
                    "Each step must contain "
                    "id, tool_name, description, input, reason, and depends_on; "
                    "input must contain tool_name and parameters, and parameters "
                    "must include every required input listed for that tool. For "
                    f"the research request, set research.parameters.goal to {request_message!r}. "
                    "Use tool_name exactly as registered: research for research and "
                    "pdf_generation for PDF creation. Never invent tool names or aliases. "
                    "Do not leave required parameters empty. Do not wrap it "
                    "in a plan key. Do not include Markdown, commentary, or a code fence."
                ),
            )
            retry_request = AIRequest(
                messages=[*messages, AIMessage(role="assistant", content=response.content), correction],
                temperature=0.0,
                max_tokens=request.max_tokens,
                response_mime_type="application/json",
                response_schema=self._plan_response_schema(),
            )
            retry_response = await self._complete_plan_request(retry_request)
            plan = self._parse_plan_response(retry_response)
            self._validate_plan(plan)
        
        logger.info(f"Created plan with {len(plan.steps)} steps")
        return plan

    async def _complete_plan_request(self, request: AIRequest) -> AIResponse:
        """Use provider JSON mode when available, then fall back to normal completion."""
        self.ai_service.primary_provider = self.ai_provider
        try:
            return await self.ai_service.complete(request)
        except Exception as exc:
            if not request.response_mime_type or not self.ai_service._is_structured_output_error(exc):
                raise
            return await self.ai_service.complete(
                replace(request, response_mime_type=None, response_schema=None)
            )

    def _plan_response_schema(self) -> dict[str, Any]:
        tools = self.tool_registry.list_tools()
        tool_names = [tool.name for tool in tools]
        parameter_schemas = []
        for tool in tools:
            parameter_schemas.append({
                "type": "object",
                "properties": tool.input_schema.properties,
                "required": tool.input_schema.required,
            })
        return {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "description": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "tool_name": {
                                "type": "string",
                                "enum": tool_names,
                            },
                            "description": {"type": "string"},
                            "input": {
                                "type": "object",
                                "properties": {
                                    "tool_name": {"type": "string", "enum": tool_names},
                                    "parameters": {"anyOf": parameter_schemas},
                                },
                                "required": ["tool_name", "parameters"],
                            },
                            "reason": {"type": "string"},
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                            "retry_on_failure": {"type": "boolean"},
                            "max_retries": {"type": "integer"},
                        },
                        "required": ["id", "tool_name", "description", "input"],
                    },
                },
                "verification_requirements": {"type": "object"},
            },
            "required": ["goal", "description", "steps", "verification_requirements"],
        }

    async def _execute_steps(
        self,
        execution: AgentExecution,
        *,
        on_status: Callable[[str, AgentExecution], Awaitable[None]] | None = None,
    ) -> None:
        """
        Execute all steps in the plan.
        
        Handles:
        - Tool selection
        - Input validation
        - Execution
        - Result passing between steps
        - Error handling and retries
        
        Args:
            execution: The execution state to update
        """
        if not execution.plan:
            raise ValueError("No plan to execute")
        
        plan = execution.plan
        
        # Build execution context with previous results
        step_results: dict[str, Any] = {}
        
        for step_index, step in enumerate(plan.steps):
            logger.info(f"Execution {execution.execution_id}: Starting step {step.id}")
            step.status = "running"
            
            step_execution = AgentStepExecution(
                id=f"execution_{step.id}",
                step_id=step.id,
                tool_name=step.tool_name,
                status=ExecutionStatus.RUNNING,
                input=step.input,
                started_at=datetime.utcnow(),
            )
            
            execution.steps.append(step_execution)
            execution.current_step_index = step_index
            if on_status:
                await on_status(ExecutionStatus.RUNNING.value, execution)
            
            # Check dependencies
            for dep_id in step.depends_on:
                if dep_id not in step_results:
                    step.status = "failed"
                    if on_status:
                        await on_status(ExecutionStatus.RUNNING.value, execution)
                    raise ValueError(f"Dependency not available: {dep_id}")
            
            # Execute with retry logic
            max_attempts = step.max_retries + 1
            for attempt in range(max_attempts):
                step_execution.attempts = attempt + 1
                
                try:
                    # Get tool
                    tool = self.tool_registry.get(step.tool_name)
                    if not tool:
                        raise ValueError(f"Tool not found: {step.tool_name}")
                    
                    # Prepare parameters (substitute previous results)
                    parameters = self._prepare_parameters(
                        step.input.parameters,
                        step_results
                    )
                    if step.tool_name == "pdf_generation" and "research" not in parameters:
                        research_output = step_results.get("research")
                        if isinstance(research_output, dict):
                            parameters["research"] = json.dumps(
                                {
                                    "report": research_output.get("report") or "",
                                    "sources": research_output.get("sources") or research_output.get("source_references") or [],
                                    "key_findings": research_output.get("key_findings") or [],
                                },
                                ensure_ascii=False,
                            )
                    
                    # Execute tool
                    if hasattr(tool, "execute_with_context"):
                        result = await tool.execute_with_context(
                            step_id=step.id,
                            parameters=parameters,
                            execution_context={"user_id": execution.user_id},
                        )
                    else:
                        result = await tool.execute_with_validation(step_id=step.id, parameters=parameters)

                    if result.success and isinstance(result.output, dict) and result.output.get("success") is False:
                        result.success = False
                        result.error = result.output.get("error") or "Tool reported failure"
                    
                    step_execution.result = result
                    # Store result for next steps using both step ID and tool name as keys
                    # This allows parameter substitution with both formats:
                    # - ${step_1.field} (step ID format)
                    # - {{research.output.field}} (tool name format)
                    output = result.output if result.success else None
                    step_results[step.id] = output
                    step_results[step.tool_name] = output  # Also store by tool name for placeholder substitution
                    
                    if result.success:
                        step.status = "completed"
                        step_execution.status = ExecutionStatus.COMPLETED
                        step_execution.completed_at = datetime.utcnow()
                        if on_status:
                            await on_status(ExecutionStatus.RUNNING.value, execution)
                        logger.info(
                            f"Execution {execution.execution_id}: "
                            f"Step {step.id} completed successfully"
                        )
                        break
                    else:
                        logger.warning(
                            f"Execution {execution.execution_id}: "
                            f"Step {step.id} failed: {result.error}"
                        )
                        step_execution.last_error = result.error
                        
                        if not step.retry_on_failure or attempt == max_attempts - 1:
                            raise Exception(f"Tool execution failed: {result.error}")
                
                except Exception as e:
                    logger.error(
                        f"Execution {execution.execution_id}: "
                        f"Step {step.id} attempt {attempt + 1} failed: {str(e)}",
                        exc_info=True
                    )
                    step_execution.last_error = str(e)
                    
                    if attempt == max_attempts - 1:
                        step.status = "failed"
                        step_execution.status = ExecutionStatus.FAILED
                        step_execution.completed_at = datetime.utcnow()
                        if on_status:
                            await on_status(ExecutionStatus.RUNNING.value, execution)
                        raise
        
        # Store final results
        execution.final_result = step_results

    async def _verify_execution(self, execution: AgentExecution) -> None:
        """
        Verify that the execution completed successfully.
        
        Args:
            execution: The execution to verify
            
        Raises:
            ValueError: If verification fails
        """
        if not execution.plan:
            raise ValueError("No plan to verify")
        
        # Check that all steps completed
        if len(execution.steps) != len(execution.plan.steps):
            raise ValueError(
                f"Not all steps executed: {len(execution.steps)} "
                f"of {len(execution.plan.steps)}"
            )
        
        # Check that all steps succeeded
        for step_exec in execution.steps:
            if step_exec.status != ExecutionStatus.COMPLETED:
                raise ValueError(
                    f"Step {step_exec.step_id} did not complete: "
                    f"{step_exec.status}"
                )
            
            if not step_exec.result or not step_exec.result.success:
                raise ValueError(
                    f"Step {step_exec.step_id} failed: "
                    f"{step_exec.result.error if step_exec.result else 'No result'}"
                )

        for step_exec in execution.steps:
            output = step_exec.result.output if step_exec.result else None
            if not isinstance(output, dict) or not output:
                raise ValueError(f"Verification failed: no output for step {step_exec.step_id}")
            file_path = output.get("file_path")
            if file_path:
                resolved = os.path.realpath(str(file_path))
                if not os.path.isfile(resolved) or os.path.getsize(resolved) <= 0:
                    raise ValueError(f"Verification failed: artifact for step {step_exec.step_id} is missing or empty")
                if str(execution.user_id) not in resolved.split(os.sep):
                    raise ValueError(f"Verification failed: artifact for step {step_exec.step_id} is not owned by the user")

    def _validate_plan(self, plan: AgentPlan) -> None:
        """
        Validate that a plan is executable.
        
        Checks:
        - Plan has steps
        - Steps have valid tool names
        - Dependencies are satisfied
        - Tool inputs are valid
        
        Args:
            plan: Plan to validate
            
        Raises:
            ValueError: If plan is invalid
        """
        if not plan.steps:
            raise ValueError("Plan must have at least one step")
        
        # Check tool availability
        available_tool_definitions = {
            tool.name: tool for tool in self.tool_registry.list_tools()
        }
        for step in plan.steps:
            tool = available_tool_definitions.get(step.tool_name)
            if tool is None:
                raise ValueError(f"Tool not available: {step.tool_name}")
            if step.input.tool_name != step.tool_name:
                raise ValueError(
                    f"Step {step.id} input tool_name must be {step.tool_name}"
                )
            missing = [
                field
                for field in tool.input_schema.required
                if field not in step.input.parameters
            ]
            if missing:
                raise ValueError(
                    f"Step {step.id} is missing required input: {', '.join(missing)}"
                )
        
        # Check dependencies are satisfied
        step_ids = {step.id for step in plan.steps}
        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    raise ValueError(
                        f"Step {step.id} depends on unknown step: {dep_id}"
                    )

    def _prepare_parameters(
        self,
        parameters: dict[str, Any],
        step_results: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Prepare tool parameters, substituting previous step results.
        
        Allows steps to reference outputs from previous steps using:
        - ${step_id.field} format (orchestrator format)
        - {{tool.output.field}} format (tool reasoning format)
        
        Args:
            parameters: Original parameters
            step_results: Results from previous steps (keyed by step_id and tool_name)
            
        Returns:
            Prepared parameters with substitutions
        """
        import re
        
        prepared = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                # Replace ${step_id.field} or {{tool.output.field}} with actual values
                def replace_placeholder(match: re.Match) -> str:
                    # Try to match {{tool.output.field}} format
                    if match.group(0).startswith("{{"):
                        tool_name = match.group(1)
                        field = match.group(2)
                        # Look up by tool name
                        if tool_name in step_results and step_results[tool_name]:
                            result = step_results[tool_name]
                            if isinstance(result, dict) and field in result:
                                return str(result[field])
                    # Try to match ${step_id.field} format
                    else:
                        step_id = match.group(1)
                        field = match.group(2)
                        if step_id in step_results and step_results[step_id]:
                            result = step_results[step_id]
                            if isinstance(result, dict) and field in result:
                                return str(result[field])
                    
                    return match.group(0)  # Return original if not found
                
                # Try both patterns
                value = re.sub(
                    r'\$\{(\w+)\.(\w+)\}',
                    replace_placeholder,
                    value
                )
                prepared[key] = re.sub(
                    r'\{\{(\w+)\.output\.(\w+)\}\}',
                    replace_placeholder,
                    value
                )
            elif isinstance(value, dict):
                prepared[key] = self._prepare_parameters(value, step_results)
            else:
                prepared[key] = value
        
        return prepared

    def _parse_plan_response(self, response: AIResponse) -> AgentPlan:
        return AgentPlan(**self._extract_json_from_response(response))

    def _extract_json_from_response(self, response: AIResponse) -> dict:
        """
        Extract JSON from AI response.
        
        Handles responses that may contain extra text before/after JSON.
        
        Args:
            response: AI response
            
        Returns:
            Parsed JSON as dict
            
        Raises:
            ValueError: If JSON cannot be extracted
        """
        content = response.content

        candidates = [content.strip()]
        candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", content, re.DOTALL | re.IGNORECASE))
        start = content.find("{")
        if start >= 0:
            decoder = json.JSONDecoder()
            try:
                _, end = decoder.raw_decode(content[start:])
                candidates.append(content[start:start + end])
            except json.JSONDecodeError:
                pass

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("The AI provider did not return a valid JSON execution plan.")
