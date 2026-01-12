from __future__ import annotations

import fitz  # PyMuPDF


def export_translated_pdf(
    *,
    source_pdf_path: str,
    output_pdf_path: str,
    chunks: list[dict],
    font_size: float = 9.5,
) -> None:
    """
    Tạo PDF đầu ra bằng cách:
    - Redact (xoá) vùng bbox của text gốc bằng nền trắng
    - Insert textbox tiếng Việt vào đúng bbox (xấp xỉ)

    NOTE: Đây là khung MVP. Một số PDF có font/encoding phức tạp có thể lệch nhẹ.
    """
    doc = fitz.open(source_pdf_path)

    # group by page
    by_page: dict[int, list[dict]] = {}
    for c in chunks:
        by_page.setdefault(int(c["page_number"]), []).append(c)

    for page_num, items in by_page.items():
        page = doc.load_page(page_num - 1)
        # Redact first
        for c in items:
            x0, y0, x1, y1 = c["bbox"]
            r = fitz.Rect(x0, y0, x1, y1)
            page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Insert translated text
        for c in items:
            vi = (c.get("vi_text") or "").strip()
            if not vi:
                continue
            x0, y0, x1, y1 = c["bbox"]
            r = fitz.Rect(x0, y0, x1, y1)
            # Keep line breaks; let textbox wrap.
            page.insert_textbox(
                r,
                vi,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
            )

    doc.save(output_pdf_path, deflate=True)
    doc.close()

