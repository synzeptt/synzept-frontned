"""PDF Generation Skill - Creates PDFs from AI-generated structured content."""

import os
from uuid import uuid4
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base import Skill
from .context import SkillContext
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult, DeliverableReference
from ..events import default_event_bus
from .registry import default_registry as skill_registry
from ..tools.pdf_generator import PDFGenerator
from ..tools.content_parser import ContentStructureParser
from ..services.ai import AIService, AIMessage, AIRequest


# auto-register
@skill_registry.autoregister("pdf_generation")
class PDFGenerationSkill(Skill):
    identity = "pdf_generation"
    purpose = "Generate structured PDF documents from AI-generated content"
    capabilities = ["pdf_generation", "content_generation", "document_creation"]
    
    def __init__(self, **dependencies: Any):
        super().__init__(**dependencies)
        self.ai_service = dependencies.get('ai_service')
        self.pdf_generator = PDFGenerator()
        self.storage_base = dependencies.get('storage_base', '/tmp/synzept-artifacts')
    
    def plan(self, context: SkillContext) -> PlanningResult:
        """Plan the PDF generation workflow."""
        planned_steps = [
            {
                "name": "understand_requirements",
                "capability": "pdf.understand",
                "inputs": {"goal": context.goal},
            },
            {
                "name": "generate_content",
                "capability": "pdf.generate_content",
                "inputs": {"goal": context.goal},
            },
            {
                "name": "structure_content",
                "capability": "pdf.structure",
                "inputs": {"goal": context.goal},
            },
            {
                "name": "create_pdf",
                "capability": "pdf.create",
                "inputs": {"goal": context.goal},
            },
            {
                "name": "verify_pdf",
                "capability": "pdf.verify",
                "inputs": {"goal": context.goal},
            },
        ]
        
        return PlanningResult(
            planned_steps=planned_steps,
            estimated_duration=60,  # 60 seconds
        )
    
    def prepare(self, context: SkillContext) -> None:
        """Prepare for PDF generation."""
        context.runtime_context.setdefault("timeline", []).append({
            "phase": "preparation",
            "label": "Preparing PDF generation",
        })
        
        # Setup storage
        Path(self.storage_base).mkdir(parents=True, exist_ok=True)
        context.runtime_context["storage_path"] = self.storage_base
        
        default_event_bus.emit("pdf.preparation_started", {
            "execution_id": context.execution_id,
            "goal": context.goal,
        })
    
    def execute(self, context: SkillContext) -> SkillResult:
        """Execute PDF generation workflow."""
        try:
            context.runtime_context.setdefault("timeline", []).append({
                "phase": "execution",
                "label": "Generating PDF content",
            })
            
            # Step 1: Generate content using AI
            content_generated = self._generate_content(context)
            if not content_generated:
                return SkillResult(
                    status=SkillExecutionStatus.FAILURE,
                    message="Failed to generate content from AI",
                )
            
            # Step 2: Parse content into structured format
            opportunities = context.runtime_context.get("opportunities", [])
            if not opportunities:
                return SkillResult(
                    status=SkillExecutionStatus.FAILURE,
                    message="Failed to parse content into structured format",
                )
            
            # Step 3: Create PDF
            pdf_path = self._create_pdf(context, opportunities)
            if not pdf_path:
                return SkillResult(
                    status=SkillExecutionStatus.FAILURE,
                    message="Failed to create PDF",
                )
            
            # Step 4: Create artifact reference
            artifact_id = str(uuid4())
            artifact = {
                "id": artifact_id,
                "type": "pdf",
                "title": "Future AI Opportunities",
                "description": "A comprehensive PDF document with 10 future opportunities in AI",
                "file_path": pdf_path,
                "file_size": os.path.getsize(pdf_path),
                "file_type": "application/pdf",
                "source": "pdf_generation_skill",
                "verification_status": "pending",
                "timestamp": context.execution_id,
            }
            
            artifacts = context.runtime_context.get("artifacts", [])
            artifacts.append(artifact)
            context.runtime_context["artifacts"] = artifacts
            context.runtime_context["artifact_id"] = artifact_id
            context.runtime_context["pdf_path"] = pdf_path
            
            return SkillResult(
                status=SkillExecutionStatus.SUCCESS,
                deliverables=[
                    DeliverableReference(
                        id=artifact_id,
                        type="pdf",
                        metadata={
                            "file_path": pdf_path,
                            "file_size": os.path.getsize(pdf_path),
                            "title": "Future AI Opportunities",
                        }
                    )
                ],
                outputs={
                    "artifacts": artifacts,
                    "pdf_path": pdf_path,
                    "opportunities_count": len(opportunities),
                },
                message="PDF generated successfully",
            )
        
        except Exception as e:
            context.logger.error(f"PDF generation error: {e}")
            return SkillResult(
                status=SkillExecutionStatus.FAILURE,
                message=f"PDF generation error: {str(e)}",
            )
    
    def verify(self, context: SkillContext) -> VerificationResult:
        """Verify the generated PDF."""
        try:
            pdf_path = context.runtime_context.get("pdf_path")
            opportunities = context.runtime_context.get("opportunities", [])
            
            if not pdf_path or not os.path.exists(pdf_path):
                return VerificationResult(
                    passed=False,
                    evidence={"pdf_exists": False},
                    message="PDF file not found",
                )
            
            file_size = os.path.getsize(pdf_path)
            if file_size <= 0:
                return VerificationResult(
                    passed=False,
                    evidence={"pdf_exists": True, "file_size": file_size},
                    message="PDF file is empty",
                )
            
            # Verify content count
            if len(opportunities) < 10:
                return VerificationResult(
                    passed=False,
                    evidence={
                        "pdf_exists": True,
                        "file_size": file_size,
                        "opportunity_count": len(opportunities),
                        "expected_count": 10,
                    },
                    message=f"Expected 10 opportunities, got {len(opportunities)}",
                )
            
            # All checks passed
            default_event_bus.emit("pdf.verified", {
                "execution_id": context.execution_id,
                "pdf_path": pdf_path,
                "file_size": file_size,
                "opportunity_count": len(opportunities),
            })
            
            return VerificationResult(
                passed=True,
                evidence={
                    "pdf_exists": True,
                    "file_size": file_size,
                    "opportunity_count": len(opportunities),
                    "opportunities": opportunities,
                },
                message="PDF verification passed",
            )
        
        except Exception as e:
            context.logger.error(f"PDF verification error: {e}")
            return VerificationResult(
                passed=False,
                evidence={"error": str(e)},
                message=f"Verification error: {str(e)}",
            )
    
    def cleanup(self, context: SkillContext) -> None:
        """Cleanup after PDF generation."""
        default_event_bus.emit("pdf.completed", {
            "execution_id": context.execution_id,
            "pdf_path": context.runtime_context.get("pdf_path"),
        })
    
    def _generate_content(self, context: SkillContext) -> bool:
        """Generate content using AI service."""
        try:
            context.runtime_context.setdefault("timeline", []).append({
                "phase": "ai_generation",
                "label": "Generating content with AI",
            })
            
            # Prepare prompt for AI
            prompt = self._prepare_prompt(context.goal)
            
            # Get AI service
            if not self.ai_service:
                # Try to get from context or create default
                from ..services.ai import AIService
                self.ai_service = AIService()
            
            # Call AI to generate content
            request = AIRequest(
                messages=[AIMessage(role="user", content=prompt)],
                model="gemini-2.5-flash",
                temperature=0.7,
            )
            
            response = self.ai_service.complete(request)
            if not response or not response.content:
                context.logger.error("No response from AI service")
                return False
            
            # Parse the response
            ai_content = response.content
            context.runtime_context["ai_generated_content"] = ai_content
            
            # Parse into structured format
            opportunities = ContentStructureParser.parse_opportunities(ai_content, expected_count=10)
            if not opportunities:
                context.logger.warning("Could not parse opportunities, attempting repair")
                # Try text parsing
                opportunities = ContentStructureParser._parse_text_format(ai_content)
            
            if not opportunities or len(opportunities) == 0:
                context.logger.error("Failed to extract opportunities from AI response")
                return False
            
            # Ensure we have 10 opportunities
            opportunities = ContentStructureParser.ensure_count(opportunities, target_count=10)
            
            # Validate and repair
            is_valid, opportunities = ContentStructureParser.validate_and_repair(opportunities)
            if not is_valid or len(opportunities) == 0:
                context.logger.error("Failed to validate opportunities")
                return False
            
            context.runtime_context["opportunities"] = opportunities
            
            context.runtime_context.setdefault("timeline", []).append({
                "phase": "parsing",
                "label": f"Parsed {len(opportunities)} opportunities",
            })
            
            return True
        
        except Exception as e:
            context.logger.error(f"Content generation error: {e}")
            return False
    
    def _create_pdf(self, context: SkillContext, opportunities: List[Dict]) -> Optional[str]:
        """Create PDF from opportunities."""
        try:
            context.runtime_context.setdefault("timeline", []).append({
                "phase": "pdf_generation",
                "label": "Creating PDF document",
            })
            
            # Generate filename
            user_id = context.runtime_context.get("user_id", "anonymous")
            filename = f"opportunities-{uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join(self.storage_base, str(user_id), filename)
            
            # Ensure directory exists
            Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Generate PDF
            success = self.pdf_generator.generate(
                output_path=pdf_path,
                title="Future AI Opportunities",
                content=opportunities,
            )
            
            if success:
                context.runtime_context.setdefault("timeline", []).append({
                    "phase": "pdf_saved",
                    "label": f"PDF saved to {pdf_path}",
                })
                return pdf_path
            
            return None
        
        except Exception as e:
            context.logger.error(f"PDF creation error: {e}")
            return None
    
    @staticmethod
    def _prepare_prompt(goal: str) -> str:
        """Prepare the prompt for AI."""
        return f"""You are an expert in AI and emerging technologies. 

Please provide exactly 10 future opportunities in Artificial Intelligence. For each opportunity:

1. Provide a clear, concise title
2. Write a short explanation (2-3 sentences) about what this opportunity entails
3. List the required skills (comma-separated list of 4-6 skills)

Format your response as a numbered list:

1. [Opportunity Title]
[Explanation of the opportunity in 2-3 sentences]
Skills required: [skill 1, skill 2, skill 3, skill 4, skill 5]

2. [Next Opportunity Title]
...and so on for all 10 opportunities.

Make sure to:
- Provide exactly 10 opportunities
- Make each explanation clear and specific
- Include realistic, in-demand skills for each opportunity
- Cover diverse areas of AI (ML, NLP, Computer Vision, AI Ethics, etc.)

User request: {goal}"""
