"""Content structure parser for converting AI responses into structured data."""

import json
import re
from typing import Optional


class ContentStructureParser:
    """Parses AI-generated content into structured format."""
    
    @staticmethod
    def parse_opportunities(content: str, expected_count: int = 10) -> Optional[list[dict]]:
        """
        Parse AI-generated opportunities from text into structured format.
        
        Args:
            content: Raw AI-generated text
            expected_count: Expected number of opportunities (default 10)
            
        Returns:
            List of dicts with 'number', 'title', 'explanation', 'skills' keys
        """
        opportunities = []
        
        # Try JSON parsing first (if AI returns JSON)
        if content.strip().startswith('[') or content.strip().startswith('{'):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    opportunities = parsed
                elif isinstance(parsed, dict) and 'opportunities' in parsed:
                    opportunities = parsed['opportunities']
                
                # Validate structure
                if opportunities and ContentStructureParser._validate_opportunities(opportunities):
                    return opportunities
            except json.JSONDecodeError:
                pass
        
        # Fall back to regex/pattern-based parsing
        opportunities = ContentStructureParser._parse_text_format(content)
        
        return opportunities if opportunities else None
    
    @staticmethod
    def _validate_opportunities(opportunities: list) -> bool:
        """Check if opportunities list has valid structure."""
        if not isinstance(opportunities, list) or len(opportunities) == 0:
            return False
        
        for opp in opportunities:
            if not isinstance(opp, dict):
                return False
            # At minimum needs title and explanation
            if 'title' not in opp and 'name' not in opp:
                return False
        
        return True
    
    @staticmethod
    def _parse_text_format(content: str) -> list[dict]:
        """Parse text-formatted opportunities (numbered list, etc)."""
        opportunities = []
        
        # Split by numbered items (1., 2., etc.)
        pattern = r'^\s*(\d+)\.\s+([^\n]+)(?:\n|$)'
        lines = content.split('\n')
        
        current_item = None
        current_number = None
        
        for i, line in enumerate(lines):
            line = line.strip()

            heading_match = re.match(r"^#{1,6}\s*(\d+)[.)]\s+(.+)$", line)
            if heading_match:
                if current_item:
                    opportunities.append(current_item)
                current_number = int(heading_match.group(1))
                current_item = {
                    'number': f"{current_number}",
                    'title': heading_match.group(2).strip("* "),
                    'explanation': '',
                    'skills': []
                }
                continue
            
            # Check if this is a numbered item start
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                # Save previous item if exists
                if current_item:
                    opportunities.append(current_item)
                
                current_number = int(match.group(1))
                title = match.group(2)
                
                current_item = {
                    'number': f"{current_number}",
                    'title': title,
                    'explanation': '',
                    'skills': []
                }
            elif current_item and line:
                # Add to current item
                if re.match(r'^(?:skills|required|abilities):', line, re.IGNORECASE):
                    # Skills line
                    skills_text = re.sub(r'^(?:skills|required|abilities):\s*', '', line, flags=re.IGNORECASE)
                    current_item['skills'] = [s.strip() for s in skills_text.split(',')]
                else:
                    # Add to explanation
                    if current_item['explanation']:
                        current_item['explanation'] += ' '
                    current_item['explanation'] += line
        
        # Add last item
        if current_item:
            opportunities.append(current_item)
        
        return opportunities
    
    @staticmethod
    def ensure_count(opportunities: list[dict], target_count: int = 10) -> list[dict]:
        """
        Ensure we have the target count of opportunities.
        If we have fewer, return what we have.
        If we have more, trim to target count.
        """
        if not opportunities:
            return []
        
        # Trim if too many
        if len(opportunities) > target_count:
            opportunities = opportunities[:target_count]
        
        # Re-number
        for i, opp in enumerate(opportunities, 1):
            opp['number'] = str(i)
        
        return opportunities
    
    @staticmethod
    def validate_and_repair(opportunities: list[dict]) -> tuple[bool, list[dict]]:
        """
        Validate opportunities list and repair if possible.
        
        Returns:
            (is_valid, opportunities_list)
        """
        if not opportunities or not isinstance(opportunities, list):
            return False, []
        
        valid_items = []
        for item in opportunities:
            if not isinstance(item, dict):
                continue
            
            # Ensure required fields
            if not item.get('title'):
                item['title'] = item.get('name', 'Untitled Opportunity')
            
            if not item.get('explanation'):
                item['explanation'] = 'See required skills for more details.'
            
            if not item.get('skills'):
                item['skills'] = []
            elif isinstance(item['skills'], str):
                item['skills'] = [s.strip() for s in item['skills'].split(',')]
            
            valid_items.append(item)
        
        return len(valid_items) > 0, valid_items
