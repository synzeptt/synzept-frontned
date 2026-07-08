"""Synzept Memory & Context Intelligence System."""

__all__ = ["MemoryEngine", "ContextEngine", "MemoryRetrievalPipeline", "MemoryIntelligenceEngine"]


def __getattr__(name: str):
    if name == "ContextEngine":
        from app.memory.context_engine import ContextEngine

        return ContextEngine
    if name == "MemoryEngine":
        from app.memory.engine import MemoryEngine

        return MemoryEngine
    if name == "MemoryRetrievalPipeline":
        from app.memory.pipeline import MemoryRetrievalPipeline

        return MemoryRetrievalPipeline
    if name == "MemoryIntelligenceEngine":
        from app.memory.intelligence_engine import MemoryIntelligenceEngine

        return MemoryIntelligenceEngine
    raise AttributeError(name)
