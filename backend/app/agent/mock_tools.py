"""
Mock/test tools for agent testing.

These tools are used to verify the agent execution engine works
without depending on external systems.
"""

from typing import Any

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema


class EchoTool(BaseTool):
    """Simple echo tool that returns input as output."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Echo tool - returns the input message unchanged. Useful for testing the agent execution loop.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "message": {"type": "string", "description": "The message to echo"}
                },
                required=["message"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "message": {"type": "string", "description": "The echoed message"},
                    "echoed": {"type": "boolean", "description": "Whether the echo was successful"},
                },
            ),
            category="utility",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute echo tool."""
        message = parameters.get("message", "")
        return {
            "message": message,
            "echoed": True,
        }


class ConcatenateTool(BaseTool):
    """Concatenates two strings."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="concatenate",
            description="Concatenate two strings. Useful for testing multi-step execution.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "text1": {"type": "string", "description": "First text"},
                    "text2": {"type": "string", "description": "Second text"},
                    "separator": {
                        "type": "string",
                        "description": "Separator between texts",
                        "default": " ",
                    },
                },
                required=["text1", "text2"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "result": {"type": "string", "description": "Concatenated result"},
                    "length": {"type": "integer", "description": "Length of result"},
                },
            ),
            category="utility",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute concatenate tool."""
        text1 = parameters.get("text1", "")
        text2 = parameters.get("text2", "")
        separator = parameters.get("separator", " ")
        
        result = f"{text1}{separator}{text2}"
        return {
            "result": result,
            "length": len(result),
        }


class CounterTool(BaseTool):
    """Tool that counts characters in text."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="counter",
            description="Count characters, words, and lines in text.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "text": {"type": "string", "description": "Text to count"},
                },
                required=["text"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "character_count": {"type": "integer"},
                    "word_count": {"type": "integer"},
                    "line_count": {"type": "integer"},
                },
            ),
            category="utility",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute counter tool."""
        text = parameters.get("text", "")
        
        return {
            "character_count": len(text),
            "word_count": len(text.split()),
            "line_count": len(text.split("\n")),
        }
