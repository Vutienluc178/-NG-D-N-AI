from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from jsonschema import validate

from .models import TRANSLATION_SCHEMA, TranslationJSON


class TranslatorService(Protocol):
    async def translate_chunk(
        self,
        *,
        chunk_id: str,
        source_text: str,
        glossary: str,
        style: str,
        context: str,
    ) -> TranslationJSON: ...


@dataclass
class DummyTranslator:
    """
    Translator mặc định để chạy được ngay (không cần API key).
    Có thể thay bằng OpenAI/local model sau qua cùng interface.
    """

    async def translate_chunk(
        self,
        *,
        chunk_id: str,
        source_text: str,
        glossary: str,
        style: str,
        context: str,
    ) -> TranslationJSON:
        notes: list[str] = []
        if not source_text.strip():
            notes.append("Chunk rỗng.")
        if len(source_text) < 30 and not context:
            notes.append("[CẦN NGỮ CẢNH] Chunk ngắn và thiếu context.")

        # Giả lập dịch: giữ nguyên ký hiệu/link/email bằng cách không đụng tới chúng.
        vi = source_text
        vi = f"[VI/{style}] {vi}"
        if glossary.strip():
            notes.append("Đã nhận glossary (dummy, chưa áp dụng).")

        payload: TranslationJSON = {"chunk_id": chunk_id, "vi_text": vi, "notes": notes}
        validate(instance=payload, schema=TRANSLATION_SCHEMA)
        return json.loads(json.dumps(payload, ensure_ascii=False))

