"""PDF generation utility for creating professional PDFs from structured content."""

import os
from pathlib import Path
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors


class PDFGenerator:
    """Generates professional PDFs from structured content."""
    
    MARGIN = 0.75 * inch
    PAGE_WIDTH = letter[0]
    PAGE_HEIGHT = letter[1]
    AVAILABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN)
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1F2937'),
            spaceAfter=12,
            alignment=1,  # centered
            fontName='Helvetica-Bold',
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            spaceBefore=6,
            fontName='Helvetica-Bold',
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=8,
            leading=14,
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSkills',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6366F1'),
            spaceAfter=4,
            fontName='Helvetica-Oblique',
        ))
    
    def generate(self, 
                 output_path: str,
                 title: str,
                 content: list[dict]) -> bool:
        """
        Generate a PDF with the given title and content.
        
        Args:
            output_path: Path where to save the PDF
            title: Document title
            content: List of dicts with 'number', 'title', 'explanation', 'skills' keys
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create the PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=self.MARGIN,
                leftMargin=self.MARGIN,
                topMargin=self.MARGIN,
                bottomMargin=self.MARGIN,
            )
            
            # Build the content
            story = []
            
            # Add title
            title_para = Paragraph(title, self.styles['CustomTitle'])
            story.append(title_para)
            story.append(Spacer(1, 0.3 * inch))
            
            # Add introduction
            intro_text = "This document presents the requested topic with structured findings, recommendations, and supporting details."
            intro = Paragraph(intro_text, self.styles['CustomBody'])
            story.append(intro)
            story.append(Spacer(1, 0.2 * inch))
            
            # Add opportunities
            for item in content:
                # Opportunity title with number
                number = item.get('number', '')
                opportunity_title = item.get('title', '')
                heading_text = f"<b>{number}. {opportunity_title}</b>"
                heading = Paragraph(heading_text, self.styles['CustomHeading'])
                story.append(heading)
                
                # Explanation
                explanation = item.get('explanation', '')
                if explanation:
                    exp_para = Paragraph(explanation, self.styles['CustomBody'])
                    story.append(exp_para)
                
                # Skills
                skills = item.get('skills', [])
                if skills:
                    skills_text = "<b>Required Skills:</b> " + ", ".join(skills)
                    skills_para = Paragraph(skills_text, self.styles['CustomSkills'])
                    story.append(skills_para)
                
                story.append(Spacer(1, 0.15 * inch))
            
            # Build the PDF
            doc.build(story)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return False
