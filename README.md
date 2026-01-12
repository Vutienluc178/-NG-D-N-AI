# PDF Dịch Việt (MVP) — Deploy Vercel + GitHub

Repo này là monorepo:

- `frontend/`: React + TypeScript (Vite)
- `backend/`: FastAPI (Python) xử lý PDF/chunk/translate/export
- `api/`: entrypoint cho Vercel Serverless (import từ `backend/`)

## Chạy local

### Backend

```bash
python3 -m pip install -r backend/requirements.txt
export APP_DB_PATH="/tmp/pdf_translate_app.sqlite"
export APP_STORAGE_DIR="/tmp/pdf_translate_storage"
python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ proxy `/api/*` sang `http://127.0.0.1:8000`.

## Deploy trên Vercel (qua GitHub)

1. Push repo lên GitHub.
2. Vào Vercel → **New Project** → import repo.
3. Vì repo dùng `vercel.json`, Vercel sẽ tự build:
   - Frontend: build Vite từ `frontend/`
   - Backend: Python serverless function từ `api/index.py`
4. Deploy.

## Lưu ý quan trọng (Vercel Serverless)

- Ở môi trường serverless, app chỉ ghi được vào **`/tmp`** và có thể bị reset giữa các lần gọi → tính năng **resume lâu dài** cần DB/storage bên ngoài (S3/Redis/Postgres) nếu bạn muốn “không mất” giữa các lần cold-start.
- PDF lớn / xử lý lâu có thể chạm giới hạn thời gian/ram của function. Khi lên production nên tách backend sang dịch vụ có worker/queue (Render/Fly/GCP) và để Vercel chỉ host frontend.

