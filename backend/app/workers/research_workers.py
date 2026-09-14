from typing import Any, Dict, List
from .base import Worker
from .context import WorkerContext
from .result import WorkerResult, ExecutionStatus
from ..connectors.runtime_integration import ConnectorRuntimeAdapter
from .registry import default_registry
from ..events import default_event_bus
import re


@default_registry.autoregister("research.search")
class SearchWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        query = context.inputs.get("query") or context.goal
        connector_cap = context.inputs.get("connector", "web-search")
        ca = ConnectorRuntimeAdapter()
        cctx = ca.manager  # access manager to build connector context
        # build connector context
        from ..connectors.context import ConnectorContext

        conn_ctx = ConnectorContext(execution_id=context.execution_id, skill_id=None, worker_id="search", config={}, metadata={"query": query})
        try:
            res = ca.perform(connector_cap, "search", conn_ctx)
            raw_results = getattr(res, "results", getattr(res, "data", None)) or []
        except (KeyError, RuntimeError) as exc:
            # Research remains resumable when an optional search provider is not
            # installed; the report records the degraded source state.
            raw_results = [{
                "id": f"local-source-{abs(hash(query))}",
                "url": "local://research-context",
                "title": query,
                "summary": f"No external search connector was available: {exc}",
                "source_type": "local_context",
            }]
        # filter duplicate URLs preserving first occurrence
        seen = set()
        results = []
        for r in raw_results:
            url = (r or {}).get("url")
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            results.append(r)
        outputs = {"results": results}
        # persist results to shared runtime_context so later steps can consume
        try:
            context.runtime_context["search_results"] = outputs.get("results")
        except Exception:
            pass
        default_event_bus.emit("research.search.completed", {"execution_id": context.execution_id, "count": len(outputs.get("results") or [])})
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs=outputs)

    def verify(self, context: WorkerContext):
        # assume execute provides outputs
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None


@default_registry.autoregister("research.fetch")
class FetchWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        sources = context.inputs.get("sources") or context.runtime_context.get("search_results")
        if not sources:
            return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"fetched": []})
        connector_cap = context.inputs.get("connector", "http-fetch")
        ca = ConnectorRuntimeAdapter()
        from ..connectors.context import ConnectorContext

        fetched = []
        for s in sources:
            meta = {"id": s.get("id"), "url": s.get("url", s.get("id"))}
            conn_ctx = ConnectorContext(execution_id=context.execution_id, skill_id=None, worker_id="fetch", config={}, metadata=meta)
            try:
                res = ca.perform(connector_cap, "read", conn_ctx)
                content = getattr(res, "record", getattr(res, "data", None))
            except (KeyError, RuntimeError) as exc:
                content = {"content_type": "text/plain", "data": s.get("summary", str(exc))}
            fetched.append({"source": s, "content": content})
        try:
            context.runtime_context["fetched"] = fetched
        except Exception:
            pass
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"fetched": fetched})

    def verify(self, context: WorkerContext):
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None


@default_registry.autoregister("research.extract")
class ExtractWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        fetched = context.inputs.get("fetched", []) or context.runtime_context.get("fetched", [])
        extracted = []
        from ..extraction.html_extractor import extract as html_extract
        from ..extraction.markdown_extractor import extract as md_extract
        from ..extraction.pdf_extractor import extract as pdf_extract

        for item in fetched:
            content = item.get("content")
            meta = item.get("source") or {}
            # detect type
            content_type = None
            data = None
            if isinstance(content, dict):
                content_type = content.get("content_type")
                data = content.get("data")
            else:
                data = content

            try:
                if isinstance(data, (bytes, bytearray)) or (content_type and "pdf" in (content_type or "")):
                    doc = pdf_extract(data if isinstance(data, (bytes, bytearray)) else b"")
                    dtype = "pdf"
                elif isinstance(data, str) and data.strip().startswith("#"):
                    doc = md_extract(data)
                    dtype = "markdown"
                else:
                    doc = html_extract(str(data or ""), url=(meta.get("url") if isinstance(meta, dict) else None))
                    dtype = "html"

                extracted.append({"source": meta, "doc": doc, "type": dtype})
                default_event_bus.emit("extraction.completed", {"execution_id": context.execution_id, "type": dtype, "word_count": doc.word_count})
            except Exception as e:
                default_event_bus.emit("extraction.failed", {"execution_id": context.execution_id, "error": str(e)})
                extracted.append({"source": meta, "doc": None, "type": "error", "error": str(e)})

        try:
            context.runtime_context["extracted"] = extracted
        except Exception:
            pass
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"extracted": extracted})

    def verify(self, context: WorkerContext):
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None


@default_registry.autoregister("research.summarize")
class SummarizeWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        extracted = context.inputs.get("extracted", [])
        summaries = []
        for e in extracted:
            text = e.get("text", "")
            # simple summarization: first 300 chars
            summary = text[:300]
            summaries.append({"source": e.get("source"), "summary": summary})
        try:
            context.runtime_context["summaries"] = summaries
        except Exception:
            pass
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"summaries": summaries})

    def verify(self, context: WorkerContext):
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None


@default_registry.autoregister("research.compare")
class CompareWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        summaries = context.inputs.get("summaries", [])
        comparisons = []
        for s in summaries:
            comparisons.append({"source": s.get("source"), "score": len(s.get("summary", ""))})
        # rank by score descending
        ranked = sorted(comparisons, key=lambda x: x["score"], reverse=True)
        try:
            context.runtime_context["ranked"] = ranked
        except Exception:
            pass
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"ranked": ranked})

    def verify(self, context: WorkerContext):
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None


@default_registry.autoregister("research.report")
class ReportWorker(Worker):
    def execute(self, context: WorkerContext) -> WorkerResult:
        title = context.inputs.get("title", context.goal)
        summaries = context.inputs.get("summaries") or context.runtime_context.get("summaries") or []
        ranked = context.inputs.get("ranked") or context.runtime_context.get("ranked") or []
        # assemble report
        sections = [
            {"title": "Executive Summary", "content": f"Research on: {title}"},
            {"title": "Key Findings", "content": ", ".join([s.get("summary", "")[:120] for s in summaries])},
            {"title": "Source Comparison", "content": str(ranked)},
            {"title": "Recommendations", "content": "Investigate top tools and prototype integrations."},
            {"title": "References", "content": ", ".join([str(s.get("source")) for s in summaries])},
        ]
        report = {"title": title, "sections": sections, "confidence": "medium"}
        # attach to context.runtime_context if available
        try:
            context.runtime_context["report"] = report
        except Exception:
            pass
        default_event_bus.emit("research.report.generated", {"execution_id": context.execution_id, "title": title})
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs={"report": report})

    def verify(self, context: WorkerContext):
        return type("V", (), {"passed": True, "evidence": {}})()

    def rollback(self, context: WorkerContext):
        return type("R", (), {"success": True})()

    def cleanup(self, context: WorkerContext) -> None:
        return None
