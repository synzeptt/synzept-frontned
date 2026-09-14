from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from html import unescape
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .base import Connector
from .context import ConnectorContext
from .result import SearchResult
from .registry import default_registry


@default_registry.autoregister("web-search")
class WebSearchConnector(Connector):
    """Simple web search connector.

    Modes:
    - api: send requests to configured search API (`endpoint`, `api_key`)
    - scrape: perform an HTML search against DuckDuckGo's HTML endpoint
    """

    def __init__(self, config: Dict[str, Any] | None = None, **deps: Any):
        super().__init__(config=config, **deps)
        self.mode = (self.config.get("mode") or "scrape").lower()
        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.2, status_forcelist=(500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def connect(self, ctx: ConnectorContext):
        return SearchResult(success=True, data=None)

    def disconnect(self, ctx: ConnectorContext):
        return SearchResult(success=True, data=None)

    def authenticate(self, ctx: ConnectorContext):
        return SearchResult(success=True, data=None)

    def refresh_credentials(self, ctx: ConnectorContext):
        return SearchResult(success=True, data=None)

    def health(self, ctx: ConnectorContext):
        return SearchResult(success=True, data=None)

    def capabilities(self) -> List[str]:
        return ["search"]

    def search(self, ctx: ConnectorContext) -> SearchResult:
        query = ctx.metadata.get("query") or ctx.config.get("query")
        if not query:
            return SearchResult(success=True, results=[])

        if self.mode == "api":
            endpoint = self.config.get("endpoint")
            api_key = self.config.get("api_key")
            params = {"q": query}
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            r = self.session.get(endpoint, params=params, headers=headers, timeout=5)
            r.raise_for_status()
            # assume JSON response with items
            data = r.json()
            items = data.get("items") or data.get("results") or []
            results = []
            for i, it in enumerate(items, start=1):
                results.append({
                    "title": it.get("title") or it.get("name"),
                    "url": it.get("link") or it.get("url"),
                    "snippet": it.get("snippet") or it.get("description"),
                    "domain": urlparse(it.get("link") or it.get("url") or "").netloc,
                    "rank": i,
                })
            return SearchResult(success=True, results=results)

        # scrape mode
        # DuckDuckGo HTML search endpoint
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        r = self.session.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        r.raise_for_status()
        html = r.text
        results = []
        anchors = list(re.finditer(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S))
        for rank, anchor in enumerate(anchors, start=1):
            block_end = anchors[rank].start() if rank < len(anchors) else len(html)
            block = html[anchor.start():block_end]
            if not anchor:
                continue
            url_val = urljoin(url, unquote(unescape(anchor.group(1))))
            redirect_query = parse_qs(urlparse(url_val).query).get("uddg", [])
            if redirect_query:
                url_val = unquote(redirect_query[0])
            title = re.sub(r"<[^>]+>", " ", anchor.group(2))
            snippet_match = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
            snippet = snippet_match.group(1) if snippet_match else ""
            snippet = re.sub(r"<[^>]+>", " ", snippet)
            results.append({
                "title": re.sub(r"\s+", " ", unescape(title)).strip(),
                "url": url_val,
                "snippet": re.sub(r"\s+", " ", unescape(snippet)).strip(),
                "domain": urlparse(url_val or "").netloc if url_val else None,
                "rank": rank,
            })

        return SearchResult(success=True, results=results)
