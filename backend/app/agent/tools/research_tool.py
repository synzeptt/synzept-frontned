"""
Research Tool for Agent Orchestrator.

This tool performs web research on a topic by:
1. Searching for relevant sources
2. Collecting and parsing source content
3. Extracting key information
4. Generating a research report

The output can be used as input to subsequent tools (e.g., PDF generation).
"""

import logging
from typing import Any, Optional
from uuid import UUID

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.execution.artifacts import ArtifactService
from app.execution.runners import ResearchRunner

logger = logging.getLogger(__name__)


class ResearchTool(BaseTool):
    """Tool for conducting web research on a topic."""

    def __init__(self, artifact_service: Optional[ArtifactService] = None):
        super().__init__()
        self.artifact_service = artifact_service
        self.runner = ResearchRunner(artifact_service=artifact_service)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="research",
            description=(
                "Conduct comprehensive web research on a topic. "
                "Searches for relevant sources, extracts key information, "
                "and generates a structured research report."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "goal": {
                        "type": "string",
                        "description": "The research topic or goal",
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["shallow", "medium", "deep"],
                        "description": "Research depth level (default: medium)",
                        "default": "medium",
                    },
                    "max_sources": {
                        "type": "integer",
                        "description": "Maximum number of sources to research (default: 10)",
                        "default": 10,
                    },
                },
                required=["goal"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "summary": {
                        "type": "string",
                        "description": "Executive summary of research findings",
                    },
                    "report": {
                        "type": "string",
                        "description": "Full research report in markdown format",
                    },
                    "sources_count": {"type": "integer"},
                    "sources": {
                        "type": "array",
                        "description": "Real source references with title, URL, and snippet",
                        "items": {"type": "object"},
                    },
                    "source_references": {
                        "type": "array",
                        "description": "Real source references with title, URL, and snippet",
                        "items": {"type": "object"},
                    },
                    "key_findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key findings",
                    },
                    "error": {"type": "string"},
                },
            ),
            category="research",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute research on the given topic."""
        goal = parameters.get("goal")
        
        if not goal:
            return {
                "success": False,
                "summary": "",
                "report": "",
                "sources_count": 0,
                    "key_findings": [],
                    "sources": [],
                    "source_references": [],
                "error": "Missing goal parameter",
            }
        
        try:
            logger.info(f"Conducting research on: {goal}")
            
            # Search for sources
            sources = await self.runner.search(goal)
            
            if not sources:
                logger.warning(f"No sources found for: {goal}")
                return {
                    "success": False,
                    "summary": self.runner.last_search_error or f"No sources found for the research goal: {goal}",
                    "report": "",
                    "sources_count": 0,
                    "key_findings": [],
                        "sources": [],
                        "source_references": [],
                    "error": self.runner.last_search_error or "No sources found",
                }
            
            # Collect source content
            pages = await self.runner.collect_sources(sources)
            
            # Extract information
            information = await self.runner.read_pages(pages, goal)
            
            # Generate report
            cleaned = self.runner.remove_duplicates(information)
            notes = self.runner.generate_notes(cleaned)
            report = self.runner.generate_report(goal, cleaned, notes, sources)
            
            # Create summary (first 300 chars of report)
            summary = report[:300] + "..." if len(report) > 300 else report
            
            # Extract key findings from notes
            key_findings = [note.strip() for note in notes[:5]] if notes else []
            
            logger.info(f"Research completed for: {goal}")
            
            return {
                "success": True,
                "summary": summary,
                "report": report,
                "sources_count": len(sources),
                    "sources": sources,
                    "source_references": sources,
                "key_findings": key_findings,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"Research tool failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "summary": "",
                "report": "",
                "sources_count": 0,
                "key_findings": [],
                    "sources": [],
                    "source_references": [],
                "error": str(e),
            }
