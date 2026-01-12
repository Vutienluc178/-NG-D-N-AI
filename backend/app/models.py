from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, TypedDict


BlockType = Literal["heading", "paragraph", "list", "table", "caption", "footnote", "unknown"]


class ChunkJSON(TypedDict):
    job_id: str
    chunk_id: str
    reading_order: int
    page_number: int
    block_type: BlockType
    bbox: list[float]  # [x0, y0, x1, y1] in PDF points (origin top-left in our normalized space)
    source_text: str
    heading_context: str
    word_count: int
    char_count: int


class TranslationJSON(TypedDict):
    chunk_id: str
    vi_text: str
    notes: list[str]


TRANSLATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["chunk_id", "vi_text", "notes"],
    "properties": {
        "chunk_id": {"type": "string"},
        "vi_text": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass(frozen=True)
class Chunk:
    job_id: str
    chunk_id: str
    reading_order: int
    page_number: int
    block_type: BlockType
    x0: float
    y0: float
    x1: float
    y1: float
    source_text: str
    heading_context: str

    def to_json(self) -> ChunkJSON:
        words = len(self.source_text.split())
        return {
            "job_id": self.job_id,
            "chunk_id": self.chunk_id,
            "reading_order": self.reading_order,
            "page_number": self.page_number,
            "block_type": self.block_type,
            "bbox": [self.x0, self.y0, self.x1, self.y1],
            "source_text": self.source_text,
            "heading_context": self.heading_context,
            "word_count": words,
            "char_count": len(self.source_text),
        }


@dataclass
class JobStatus:
    job_id: str
    filename: str
    page_count: int
    detected_columns: int
    chunk_count: int
    translated_count: int
    current_chunk_id: Optional[str]
    state: Literal["uploaded", "analyzed", "translating", "paused", "exporting", "done", "error"]
    error_message: Optional[str]
