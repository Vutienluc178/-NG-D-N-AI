from __future__ import annotations

import asyncio
import json
import time
import uuid
import os
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from . import db
from .models import Chunk, JobStatus
from .pdf_analyzer import analyze_pdf
from .pdf_exporter import export_translated_pdf
from .translator import DummyTranslator


APP_NAME = "PDF Dịch Việt (MVP)"
STORAGE_DIR = Path(os.environ.get("APP_STORAGE_DIR", "/tmp/pdf_translate_storage" if os.environ.get("VERCEL") else "/workspace/backend/storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

translator = DummyTranslator()
translation_tasks: dict[str, asyncio.Task] = {}


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def _job_status(job_id: str) -> JobStatus:
    row = db.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    return JobStatus(
        job_id=row["job_id"],
        filename=row["filename"],
        page_count=int(row["page_count"] or 0),
        detected_columns=int(row["detected_columns"] or 1),
        chunk_count=int(row["chunk_count"] or 0),
        translated_count=int(row["translated_count"] or 0),
        current_chunk_id=row["current_chunk_id"],
        state=row["state"],
        error_message=row["error_message"],
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "name": APP_NAME}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Vui lòng tải file PDF.")

    job_id = uuid.uuid4().hex
    pdf_path = STORAGE_DIR / f"{job_id}.pdf"
    content = await file.read()
    pdf_path.write_bytes(content)

    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs(job_id, created_at, filename, pdf_path, state)
            VALUES(?,?,?,?,?)
            """,
            (job_id, int(time.time()), file.filename, str(pdf_path), "uploaded"),
        )
    return {"job_id": job_id}


@app.post("/api/analyze/{job_id}")
async def analyze(
    job_id: str,
    max_words: int = Form(1500),
    max_chars: int = Form(8000),
) -> dict[str, Any]:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")

    pdf_path = job["pdf_path"]
    try:
        res = analyze_pdf(job_id=job_id, pdf_path=pdf_path, max_words=max_words, max_chars=max_chars)
    except Exception as e:
        with db.get_conn() as conn:
            conn.execute("UPDATE jobs SET state=?, error_message=? WHERE job_id=?", ("error", str(e), job_id))
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích PDF: {e}")

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET page_count=?, detected_columns=?, chunk_count=?, translated_count=?, state=? WHERE job_id=?",
            (res.page_count, res.detected_columns, len(res.chunks), 0, "analyzed", job_id),
        )
        conn.execute("DELETE FROM chunks WHERE job_id=?", (job_id,))
        for c in res.chunks:
            conn.execute(
                """
                INSERT INTO chunks(job_id, chunk_id, reading_order, page_number, block_type,
                                  x0,y0,x1,y1, source_text, heading_context, status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    c.job_id,
                    c.chunk_id,
                    c.reading_order,
                    c.page_number,
                    c.block_type,
                    c.x0,
                    c.y0,
                    c.x1,
                    c.y1,
                    c.source_text,
                    c.heading_context,
                    "pending",
                ),
            )

    return {
        "job_id": job_id,
        "page_count": res.page_count,
        "detected_columns": res.detected_columns,
        "chunk_count": len(res.chunks),
    }


@app.get("/api/chunks/{job_id}")
def list_chunks(job_id: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
    if not db.get_job(job_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT chunk_id, reading_order, page_number, block_type, x0,y0,x1,y1,
                   source_text, heading_context, vi_text, status
            FROM chunks
            WHERE job_id=?
            ORDER BY reading_order
            LIMIT ? OFFSET ?
            """,
            (job_id, limit, offset),
        ).fetchall()
    return {
        "items": [
            {
                "chunk_id": r["chunk_id"],
                "reading_order": r["reading_order"],
                "page_number": r["page_number"],
                "block_type": r["block_type"],
                "bbox": [r["x0"], r["y0"], r["x1"], r["y1"]],
                "source_text": r["source_text"],
                "heading_context": r["heading_context"],
                "vi_text": r["vi_text"],
                "status": r["status"],
            }
            for r in rows
        ]
    }


async def _translation_loop(job_id: str, style: str, glossary: str) -> None:
    with db.get_conn() as conn:
        conn.execute("UPDATE jobs SET state=?, paused=0, error_message=NULL WHERE job_id=?", ("translating", job_id))

    while True:
        job = db.get_job(job_id)
        if not job:
            return
        if int(job["paused"] or 0) == 1:
            with db.get_conn() as conn:
                conn.execute("UPDATE jobs SET state=? WHERE job_id=?", ("paused", job_id))
            await asyncio.sleep(0.5)
            continue

        with db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM chunks
                WHERE job_id=? AND status IN ('pending','error')
                ORDER BY reading_order
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()

        if not row:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE jobs SET state=?, current_chunk_id=NULL WHERE job_id=?",
                    ("analyzed", job_id),
                )
            return

        chunk_id = row["chunk_id"]
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET current_chunk_id=? WHERE job_id=?",
                (chunk_id, job_id),
            )
            conn.execute(
                "UPDATE chunks SET status=? WHERE job_id=? AND chunk_id=?",
                ("translating", job_id, chunk_id),
            )

        try:
            payload = await translator.translate_chunk(
                chunk_id=chunk_id,
                source_text=row["source_text"],
                glossary=glossary or "",
                style=style or "Tự nhiên",
                context=row["heading_context"] or "",
            )
            vi_text = payload["vi_text"]
            notes_json = json.dumps(payload["notes"], ensure_ascii=False)
            with db.get_conn() as conn:
                conn.execute(
                    """
                    UPDATE chunks SET vi_text=?, notes_json=?, status=?
                    WHERE job_id=? AND chunk_id=?
                    """,
                    (vi_text, notes_json, "done", job_id, chunk_id),
                )
                conn.execute(
                    """
                    UPDATE jobs
                    SET translated_count=(SELECT COUNT(*) FROM chunks WHERE job_id=? AND status='done')
                    WHERE job_id=?
                    """,
                    (job_id, job_id),
                )
        except Exception as e:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE chunks SET status=? WHERE job_id=? AND chunk_id=?",
                    ("error", job_id, chunk_id),
                )
                conn.execute("UPDATE jobs SET error_message=? WHERE job_id=?", (str(e), job_id))
            await asyncio.sleep(0.8)  # basic retry backoff


@app.post("/api/translate/{job_id}/start")
async def start_translate(
    job_id: str,
    style: str = Form("Tự nhiên"),
    glossary: str = Form(""),
) -> dict[str, Any]:
    if not db.get_job(job_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    if job_id in translation_tasks and not translation_tasks[job_id].done():
        return {"ok": True, "job_id": job_id, "message": "Đang dịch."}
    t = asyncio.create_task(_translation_loop(job_id, style, glossary))
    translation_tasks[job_id] = t
    return {"ok": True, "job_id": job_id}


@app.post("/api/translate/{job_id}/pause")
def pause(job_id: str) -> dict[str, Any]:
    if not db.get_job(job_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    with db.get_conn() as conn:
        conn.execute("UPDATE jobs SET paused=1 WHERE job_id=?", (job_id,))
    return {"ok": True}


@app.post("/api/translate/{job_id}/resume")
async def resume(job_id: str) -> dict[str, Any]:
    if not db.get_job(job_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    with db.get_conn() as conn:
        conn.execute("UPDATE jobs SET paused=0 WHERE job_id=?", (job_id,))
    # ensure a task exists
    if job_id not in translation_tasks or translation_tasks[job_id].done():
        t = asyncio.create_task(_translation_loop(job_id, "Tự nhiên", ""))
        translation_tasks[job_id] = t
    return {"ok": True}


@app.get("/api/status/{job_id}")
def status(job_id: str) -> dict[str, Any]:
    s = _job_status(job_id)
    pct = 0.0 if s.chunk_count == 0 else (s.translated_count / s.chunk_count) * 100.0
    return {
        "job_id": s.job_id,
        "filename": s.filename,
        "page_count": s.page_count,
        "detected_columns": s.detected_columns,
        "chunk_count": s.chunk_count,
        "translated_count": s.translated_count,
        "progress_percent": round(pct, 2),
        "current_chunk_id": s.current_chunk_id,
        "state": s.state,
        "error_message": s.error_message,
    }


@app.post("/api/export/{job_id}")
def export(job_id: str) -> dict[str, Any]:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    pdf_path = job["pdf_path"]
    out_path = STORAGE_DIR / f"{job_id}.vi.pdf"

    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT page_number, x0,y0,x1,y1, vi_text, source_text
            FROM chunks
            WHERE job_id=?
            ORDER BY reading_order
            """,
            (job_id,),
        ).fetchall()
    chunks = [
        {
            "page_number": r["page_number"],
            "bbox": [r["x0"], r["y0"], r["x1"], r["y1"]],
            "vi_text": r["vi_text"] or "",
            "source_text": r["source_text"],
        }
        for r in rows
    ]

    try:
        with db.get_conn() as conn:
            conn.execute("UPDATE jobs SET state=? WHERE job_id=?", ("exporting", job_id))
        export_translated_pdf(source_pdf_path=pdf_path, output_pdf_path=str(out_path), chunks=chunks)
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET output_pdf_path=?, state=? WHERE job_id=?",
                (str(out_path), "done", job_id),
            )
    except Exception as e:
        with db.get_conn() as conn:
            conn.execute("UPDATE jobs SET state=?, error_message=? WHERE job_id=?", ("error", str(e), job_id))
        raise HTTPException(status_code=500, detail=f"Lỗi xuất PDF: {e}")

    return {"ok": True, "job_id": job_id}


@app.get("/api/download/{job_id}")
def download(job_id: str) -> FileResponse:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    out_path = job["output_pdf_path"]
    if not out_path or not Path(out_path).exists():
        raise HTTPException(status_code=404, detail="Chưa có file xuất. Hãy Export trước.")
    return FileResponse(
        out_path,
        media_type="application/pdf",
        filename=f"{Path(job['filename']).stem}.vi.pdf",
    )


@app.get("/api/preview/{job_id}/{page_number}.png")
def preview_page(job_id: str, page_number: int) -> Response:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    doc = fitz.open(job["pdf_path"])
    if page_number < 1 or page_number > doc.page_count:
        doc.close()
        raise HTTPException(status_code=400, detail="Số trang không hợp lệ.")
    page = doc.load_page(page_number - 1)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return Response(content=png_bytes, media_type="image/png")

