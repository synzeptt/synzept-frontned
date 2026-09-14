"""
PDF Generation Tool for Agent Orchestrator.

This tool generates PDFs from user requests by:
1. Using Gemini AI to generate structured content
2. Using PDFGenerator to create the PDF file
3. Returning the file path and metadata
"""

import os
import json
import logging
from uuid import uuid4
from typing import Any

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.services.ai.ai_service import AIService
from app.services.ai.base_provider import AIMessage, AIRequest
from app.tools.pdf_generator import PDFGenerator
from app.tools.content_parser import ContentStructureParser

logger = logging.getLogger(__name__)


class PDFGenerationTool(BaseTool):
    """Tool for generating PDF documents from user requests."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="pdf_generation",
            description=(
                "Generate a professional PDF document from a topic. "
                "Generates structured content and creates a PDF file."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "topic": {
                        "type": "string",
                        "description": "The topic or title for the PDF"
                    },
                    "num_items": {
                        "type": "integer",
                        "description": "Number of items to include (default: 10)",
                        "default": 10,
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Type: 'opportunities', 'tools', 'guide', 'analysis'",
                        "default": "opportunities",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for storage",
                    },
                    "research": {
                        "type": "string",
                        "description": "Research report and source references to use in the PDF",
                    },
                },
                required=["topic", "user_id"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "file_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "items_count": {"type": "integer"},
                    "error": {"type": "string"},
                },
            ),
            category="document",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute PDF generation."""
        topic = parameters.get("topic")
        user_id = parameters.get("user_id")
        num_items = parameters.get("num_items", 10)
        content_type = parameters.get("content_type", "opportunities")
        research_context = parameters.get("research") or parameters.get("research_report") or ""
        if isinstance(research_context, (dict, list)):
            research_context = json.dumps(research_context, ensure_ascii=False)
        
        if not topic or not user_id:
            return {
                "success": False,
                "file_path": None,
                "filename": None,
                "file_size": 0,
                "items_count": 0,
                "error": "Missing topic or user_id",
            }
        
        try:
            logger.info(f"Generating PDF for user {user_id}: {topic}")
            
            # Generate content using AI
            content = await self._generate_content(topic, num_items, content_type, research_context)
            
            if not content:
                return {
                    "success": False,
                    "file_path": None,
                    "filename": None,
                    "file_size": 0,
                    "items_count": 0,
                    "error": "Failed to generate content",
                }
            
            # Create PDF file
            filename = f"{topic.lower().replace(' ', '-')[:30]}-{uuid4().hex[:8]}.pdf"
            storage_base = "/tmp/synzept-artifacts"
            pdf_path = os.path.join(storage_base, user_id, filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            generator = PDFGenerator()
            success = generator.generate(
                output_path=pdf_path,
                title=topic,
                content=content,
            )
            
            if not success or not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
                return {
                    "success": False,
                    "file_path": None,
                    "filename": None,
                    "file_size": 0,
                    "items_count": 0,
                    "error": "PDF generation failed",
                }
            
            file_size = os.path.getsize(pdf_path)
            logger.info(f"PDF created: {pdf_path} ({file_size} bytes)")
            
            return {
                "success": True,
                "artifact_id": str(uuid4()),
                "file_path": pdf_path,
                "filename": filename,
                "file_size": file_size,
                "items_count": len(content),
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "file_path": None,
                "filename": None,
                "file_size": 0,
                "items_count": 0,
                "error": str(e),
            }

    async def _generate_content(
        self,
        topic: str,
        num_items: int,
        content_type: str,
        research_context: str = "",
    ) -> list[dict[str, Any]]:
        """Generate structured content using AI."""
        if research_context:
            prompt = (
                f"Create a factual PDF report titled '{topic}' from the supplied research evidence. "
                f"Select and compare exactly {num_items} relevant items when the evidence supports that many. "
                "For each item include: title, concise description, key specifications or facts, "
                "a recommendation, and cited source URLs. Do not invent facts or sources; state when evidence is missing. "
                "Return plain text with numbered items."
            )
        elif content_type == "opportunities":
            prompt = (
                f"Create a document titled '{topic}'. "
                f"Provide exactly {num_items} items with format:\n"
                f"1. Item Name\nExplanation...\nSkills: skill1, skill2, skill3\n\n"
                f"Must have exactly {num_items} items."
            )
        else:
            prompt = (
                f"Create a document about '{topic}' with exactly {num_items} numbered sections. "
                "For every section use this plain-text format:\n"
                "1. Section title\nDescription: ...\nDetails: ...\n"
                "Pros: ...\nCons: ...\nRecommendation: ...\n"
                "Sources: URL or source title\n"
                "Use the supplied research evidence when present."
            )
        if research_context:
            prompt += f"\n\nResearch evidence to use and cite:\n{research_context[:12000]}"
        
        try:
            ai_service = AIService()
            request = AIRequest(
                messages=[AIMessage(role="user", content=prompt)],
                temperature=0.7,
                max_tokens=3000,
            )
            
            response = await ai_service.complete(request)
            raw_content = response.content.strip()
            
            if not raw_content:
                logger.error("AI returned empty content")
                return []
            
            # Parse content
            items = ContentStructureParser.parse_opportunities(raw_content, expected_count=num_items)
            if not items:
                items = ContentStructureParser._parse_text_format(raw_content)
            
            items = ContentStructureParser.ensure_count(items or [], target_count=num_items)
            logger.info(f"Generated {len(items)} items")
            return items
            
        except Exception as e:
            logger.error(f"Content generation error: {str(e)}", exc_info=True)
            return []
