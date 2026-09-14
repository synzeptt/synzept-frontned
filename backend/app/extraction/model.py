from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class StructuredDocument:
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    canonical_url: Optional[str] = None
    language: Optional[str] = None
    headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    lists: List[List[str]] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    estimated_reading_time: Optional[int] = None
    word_count: int = 0
    text: Optional[str] = None
    extraction_confidence: float = 1.0
