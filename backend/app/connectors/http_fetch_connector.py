from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .base import Connector
from .context import ConnectorContext
from .result import ReadResult
from .registry import default_registry


@default_registry.autoregister("http-fetch")
class HTTPFetchConnector(Connector):
    """HTTP fetch connector with timeout, retries, UA, max size and redirect handling."""

    def __init__(self, config: Dict[str, Any] | None = None, **deps: Any):
        super().__init__(config=config, **deps)
        self.timeout = self.config.get("timeout", 10)
        self.max_size = int(self.config.get("max_size", 5 * 1024 * 1024))
        self.user_agent = self.config.get("user_agent", "SynzeptResearch/1.0")
        self.session = requests.Session()
        retries = Retry(total=self.config.get("retries", 2), backoff_factor=0.2, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def capabilities(self) -> list[str]:
        return ["read"]

    def connect(self, ctx: ConnectorContext):
        return ReadResult(success=True)

    def disconnect(self, ctx: ConnectorContext):
        return ReadResult(success=True)

    def authenticate(self, ctx: ConnectorContext):
        return ReadResult(success=True)

    def refresh_credentials(self, ctx: ConnectorContext):
        return ReadResult(success=True)

    def health(self, ctx: ConnectorContext):
        return ReadResult(success=True)

    def read(self, ctx: ConnectorContext) -> ReadResult:
        url = ctx.metadata.get("url") or ctx.metadata.get("id")
        if not url:
            return ReadResult(success=False, message="missing url")
        headers = {"User-Agent": self.user_agent}
        try:
            with self.session.get(url, headers=headers, timeout=self.timeout, stream=True, allow_redirects=True) as r:
                status = r.status_code
                content_type = r.headers.get("content-type")
                chunks = []
                total = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        total += len(chunk)
                        if total > self.max_size:
                            return ReadResult(success=False, message="max size exceeded")
                        chunks.append(chunk)
                data = b"".join(chunks)
                # for text types, decode
                if content_type and content_type.startswith("text"):
                    try:
                        data = data.decode(r.encoding or "utf-8", errors="replace")
                    except Exception:
                        data = data.decode("utf-8", errors="replace")
                return ReadResult(success=True, record={"url": url, "status": status, "content_type": content_type, "data": data})
        except requests.Timeout:
            return ReadResult(success=False, message="timeout")
        except requests.RequestException as e:
            return ReadResult(success=False, message=str(e))
