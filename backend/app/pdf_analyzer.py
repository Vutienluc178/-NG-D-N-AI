from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Literal

import fitz  # PyMuPDF

from .models import BlockType, Chunk


def _norm_bbox(page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, float, float]:
    """
    Chuẩn hoá bbox sang hệ toạ độ top-left (y tăng xuống), dễ dùng trong UI.
    PyMuPDF dùng origin top-left, nên giữ nguyên (x0,y0,x1,y1).
    """
    r = rect
    return (float(r.x0), float(r.y0), float(r.x1), float(r.y1))


def detect_columns(page: fitz.Page) -> int:
    """
    Heuristic: nếu có 2 cụm x0 rõ rệt (trái/phải) thì coi là 2 cột.
    """
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    x0s: list[float] = []
    for b in blocks:
        text = (b[4] or "").strip()
        if not text:
            continue
        x0s.append(float(b[0]))
    if len(x0s) < 6:
        return 1
    x0s.sort()
    # tách bằng khoảng gap lớn nhất
    gaps = [(x0s[i + 1] - x0s[i], i) for i in range(len(x0s) - 1)]
    max_gap, idx = max(gaps, key=lambda t: t[0])
    if max_gap < 80:  # points
        return 1
    left = x0s[: idx + 1]
    right = x0s[idx + 1 :]
    if not left or not right:
        return 1
    # hai cụm đủ “tách”
    if (sum(right) / len(right)) - (sum(left) / len(left)) > 120:
        return 2
    return 1


def _classify_block(text: str) -> BlockType:
    t = text.strip()
    if not t:
        return "unknown"
    # heading: ngắn, có thể in hoa nhiều
    if len(t) <= 80 and (t.isupper() or re.match(r"^\d+(\.\d+)*\s+\S+", t)):
        return "heading"
    # list
    if re.match(r"^(\-|\*|\u2022)\s+", t) or re.match(r"^\d+[\.\)]\s+", t):
        return "list"
    # footnote: bắt đầu bằng số nhỏ hoặc ký hiệu
    if re.match(r"^\d+\s+", t) and len(t) <= 140:
        return "footnote"
    return "paragraph"


@dataclass(frozen=True)
class AnalyzeResult:
    page_count: int
    detected_columns: int
    chunks: list[Chunk]


def analyze_pdf(
    *,
    job_id: str,
    pdf_path: str,
    max_words: int = 1500,
    max_chars: int = 8000,
) -> AnalyzeResult:
    doc = fitz.open(pdf_path)
    chunks: list[Chunk] = []
    reading_order = 0
    detected_cols_overall = 1
    last_heading = ""

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        cols = detect_columns(page)
        detected_cols_overall = max(detected_cols_overall, cols)

        blocks = page.get_text("blocks")
        # blocks are already roughly in reading order, but 2-column can be messy.
        # We enforce order by (col, y0, x0) where col determined by x0 split.
        page_width = float(page.rect.width)
        split_x = page_width / 2.0

        def col_of(x0: float) -> int:
            if cols == 1:
                return 0
            return 0 if x0 < split_x else 1

        sortable = []
        for b in blocks:
            x0, y0, x1, y1, text = float(b[0]), float(b[1]), float(b[2]), float(b[3]), (b[4] or "")
            text = text.strip()
            if not text:
                continue
            sortable.append((col_of(x0), y0, x0, x1, y1, text))
        sortable.sort(key=lambda t: (t[0], t[1], t[2]))

        # Merge consecutive blocks of same type into chunks with limits.
        cur_type: BlockType | None = None
        cur_text_parts: list[str] = []
        cur_bbox: fitz.Rect | None = None
        cur_heading_ctx = last_heading

        def flush() -> None:
            nonlocal reading_order, cur_type, cur_text_parts, cur_bbox, cur_heading_ctx, last_heading
            if not cur_text_parts or cur_bbox is None or cur_type is None:
                cur_text_parts = []
                cur_bbox = None
                cur_type = None
                return
            text = "\n".join(cur_text_parts).strip()
            if not text:
                cur_text_parts = []
                cur_bbox = None
                cur_type = None
                return
            x0, y0, x1, y1 = _norm_bbox(page, cur_bbox)
            chunk_id = f"p{page_index+1}-c{reading_order+1}"
            chunks.append(
                Chunk(
                    job_id=job_id,
                    chunk_id=chunk_id,
                    reading_order=reading_order,
                    page_number=page_index + 1,
                    block_type=cur_type,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    source_text=text,
                    heading_context=cur_heading_ctx,
                )
            )
            reading_order += 1
            if cur_type == "heading":
                last_heading = text[:200]
            cur_text_parts = []
            cur_bbox = None
            cur_type = None

        for col, y0, x0, x1, y1, text in sortable:
            btype = _classify_block(text)
            # Cập nhật context sớm nếu gặp heading
            if btype == "heading":
                flush()
                cur_type = "heading"
                cur_text_parts = [text]
                cur_bbox = fitz.Rect(x0, y0, x1, y1)
                cur_heading_ctx = last_heading
                flush()
                continue

            # bắt đầu chunk mới nếu loại đổi
            if cur_type is None:
                cur_type = btype
                cur_text_parts = [text]
                cur_bbox = fitz.Rect(x0, y0, x1, y1)
                cur_heading_ctx = last_heading
                continue

            same_type = (btype == cur_type)
            prospective = ("\n".join(cur_text_parts + [text])).strip()
            too_big = (len(prospective) > max_chars) or (len(prospective.split()) > max_words)

            if (not same_type) or too_big:
                flush()
                cur_type = btype
                cur_text_parts = [text]
                cur_bbox = fitz.Rect(x0, y0, x1, y1)
                cur_heading_ctx = last_heading
            else:
                cur_text_parts.append(text)
                cur_bbox = cur_bbox | fitz.Rect(x0, y0, x1, y1)

        flush()

    doc.close()
    return AnalyzeResult(page_count=doc.page_count, detected_columns=detected_cols_overall, chunks=chunks)

