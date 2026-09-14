import re
from typing import Optional
from .model import StructuredDocument


def _strip_scripts_styles(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return html


def _extract_title(html: str) -> Optional[str]:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return m.group(1).strip() if m else None


def _extract_meta(html: str, name: str) -> Optional[str]:
    m = re.search(rf"<meta[^>]+(?:name|property)=[\"']{name}[\"'][^>]*content=[\"'](.*?)[\"']", html, flags=re.I)
    if m:
        return m.group(1).strip()
    # try name attr first
    m2 = re.search(rf"<meta[^>]*content=[\"'](.*?)[\"'][^>]*name=[\"']{name}[\"']", html, flags=re.I)
    if m2:
        return m2.group(1).strip()
    return None


def _text_from_html(html: str) -> str:
    # naive removal of tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract(html: str, url: Optional[str] = None) -> StructuredDocument:
    s = StructuredDocument()
    s.url = url
    clean = _strip_scripts_styles(html)
    s.title = _extract_title(clean)
    s.author = _extract_meta(clean, "author") or _extract_meta(clean, "article:author")
    s.published_date = _extract_meta(clean, "article:published_time") or _extract_meta(clean, "pubdate")
    s.canonical_url = _extract_meta(clean, "og:url")
    s.language = _extract_meta(clean, "language") or _extract_meta(clean, "og:locale")

    # find main article content heuristically: <article> or largest <div>
    article_match = re.search(r"<article[^>]*>(.*?)</article>", clean, flags=re.I | re.S)
    main_html = article_match.group(1) if article_match else None
    if not main_html:
        # find all <div> blocks and pick the one with most text
        divs = re.findall(r"<div[^>]*>(.*?)</div>", clean, flags=re.I | re.S)
        max_text = ""
        for d in divs:
            t = _text_from_html(d)
            if len(t) > len(max_text):
                max_text = t
        main_html = max_text or clean

    # headings
    headings = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", main_html, flags=re.I | re.S)
    s.headings = [re.sub(r"<[^>]+>", "", h).strip() for h in headings]

    # paragraphs
    paras = re.findall(r"<p[^>]*>(.*?)</p>", main_html, flags=re.I | re.S)
    s.paragraphs = [re.sub(r"<[^>]+>", "", p).strip() for p in paras if re.sub(r"<[^>]+>", "", p).strip()]

    # lists
    lists = re.findall(r"<ul[^>]*>(.*?)</ul>", main_html, flags=re.I | re.S)
    for l in lists:
        items = re.findall(r"<li[^>]*>(.*?)</li>", l, flags=re.I | re.S)
        s.lists.append([re.sub(r"<[^>]+>", "", it).strip() for it in items])

    # images metadata
    imgs = re.findall(r"<img[^>]+>", main_html, flags=re.I)
    for im in imgs:
        src_m = re.search(r"src=[\"'](.*?)[\"']", im)
        alt_m = re.search(r"alt=[\"'](.*?)[\"']", im)
        s.images.append({"src": src_m.group(1) if src_m else None, "alt": alt_m.group(1) if alt_m else None})

    # links
    links = re.findall(r"<a[^>]+href=[\"'](.*?)[\"']", main_html, flags=re.I)
    s.links = links

    # text and metrics
    text = _text_from_html(main_html)
    s.text = text
    words = text.split()
    s.word_count = len(words)
    s.estimated_reading_time = max(1, s.word_count // 200)

    # basic deduplication: remove repeated paragraphs
    seen = set()
    unique_paras = []
    for p in s.paragraphs:
        if p in seen:
            continue
        seen.add(p)
        unique_paras.append(p)
    s.paragraphs = unique_paras

    return s
