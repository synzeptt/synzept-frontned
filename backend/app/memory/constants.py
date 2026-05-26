"""Memory system constants and category taxonomy."""

MEMORY_TYPE_SHORT = "short_term"
MEMORY_TYPE_LONG = "long_term"
MEMORY_TYPE_PROJECT = "project"

# Long-term memory categories
CATEGORIES = frozenset({
    "identity",
    "work",
    "projects",
    "preferences",
    "goals",
    "routines",
    "decisions",
    "priorities",
    "relationships",
    "productivity",
    "productivity_patterns",
    "other",
})

# Scoring weights (must sum to ~1.0 for composite)
WEIGHT_SEMANTIC = 0.32
WEIGHT_LEXICAL = 0.18
WEIGHT_IMPORTANCE = 0.22
WEIGHT_RECENCY = 0.14
WEIGHT_ACCESS = 0.08
WEIGHT_PROJECT = 0.06

# Retrieval thresholds
MIN_RELEVANCE_SCORE = 0.42
MIN_SEMANTIC_SCORE = 0.38
MAX_MEMORIES_IN_CONTEXT = 6
MAX_SEMANTIC_HITS = 5
MAX_SHORT_TERM_MESSAGES = 14
SHORT_TERM_CHAR_BUDGET = 6000

# Deduplication
DEDUP_SIMILARITY_THRESHOLD = 0.82
