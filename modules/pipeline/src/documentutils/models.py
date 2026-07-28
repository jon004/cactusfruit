from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Chunk:
    """The output of the Chunker. body is raw text, text is prefixed for the LLM."""
    raw_text: str
    prefixed_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0

@dataclass
class EmbeddedChunk:
    """The final package. Text + Metadata + Mathematical Vector."""
    prefixed_text: str # The text to be embedded (prefixed for the LLM)
    raw_text: str # The raw text (without prefix)
    metadata: Dict[str, Any]
    vector: List[float]

@dataclass
class ScoredText:
    """The polished result of a semantic search."""
    with_siblings: List[str] # The matched chunk + its siblings (siblings = adjacent chunks)
    matching_chunk: str # The matched chunk
    metadata: Dict[str, Any]
    score: float # The vector similarity score for the matching chunk
