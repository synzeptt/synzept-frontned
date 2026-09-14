import re
from typing import Optional
from .model import StructuredDocument


def extract(markdown_text: str, url: Optional[str] = None) -> StructuredDocument:
    s = StructuredDocument()
    s.url = url
    lines = markdown_text.splitlines()
    current_para = []
    for line in lines:
        if line.strip().startswith("#"):
            # heading
            if current_para:
                s.paragraphs.append(" ".join(current_para).strip())
                current_para = []
            heading = line.lstrip('#').strip()
            s.headings.append(heading)
        elif re.match(r"^[-*+]\s+", line):
            # list item
            item = re.sub(r"^[-*+]\s+", "", line).strip()
            if not s.lists or not isinstance(s.lists[-1], list):
                s.lists.append([])
            s.lists[-1].append(item)
        elif re.match(r"^\|.*\|", line):
            # table row - naive parsing
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not s.tables:
                s.tables.append([])
            s.tables[-1].append(cells)
        else:
            if line.strip() == "":
                if current_para:
                    s.paragraphs.append(" ".join(current_para).strip())
                    current_para = []
            else:
                current_para.append(line.strip())

    if current_para:
        s.paragraphs.append(" ".join(current_para).strip())

    text = "\n\n".join(s.paragraphs)
    s.text = text
    s.word_count = len(text.split())
    s.estimated_reading_time = max(1, s.word_count // 200)
    return s
