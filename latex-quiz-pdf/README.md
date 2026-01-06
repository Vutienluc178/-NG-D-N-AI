# LaTeX Quiz → PDF (16:9)

Web app soạn **câu hỏi có công thức LaTeX** (trắc nghiệm/đúng-sai/trả lời ngắn), xem **preview dạng slide 16:9**, và **xuất PDF trình chiếu** bằng Print-to-PDF.

## Tính năng

- **Soạn thảo**: Markdown + LaTeX (`$...$`, `$$...$$`)
- **Loại câu hỏi**:
  - `[MC]` trắc nghiệm
  - `[TF]` đúng/sai
  - `[SA]` trả lời ngắn
- **Tách slide**: một dòng chỉ có `---`
- **Đáp án**: dòng `**Đáp án:** ...` hoặc `Đáp án: ...` (có thể bật/tắt hiển thị)
- **Xuất PDF 16:9**: mở `/print` và bấm **In / Lưu PDF**

## Chạy local

```bash
cd latex-quiz-pdf
npm install
npm run dev
```

Mở `http://localhost:3000`.

## Xuất PDF (16:9)

Trong app bấm **Xuất PDF (mở trang in)** → bấm **In / Lưu PDF**.

Gợi ý trong hộp thoại Print:
- **Destination**: Save as PDF
- **Scale**: 100%
- Tắt **Headers and footers** (nếu có)

## Deploy Vercel

### Cách 1: Import từ GitHub

- Push repo lên GitHub
- Vercel → **New Project** → Import repo
- Nếu repo có nhiều thư mục, đặt **Root Directory** = `latex-quiz-pdf`

### Cách 2: Vercel CLI

```bash
cd latex-quiz-pdf
npx vercel
```

## Ghi chú

- PDF được tạo bằng **CSS print** (tương thích Vercel, không cần server-side Chromium).
- Kích thước trang in đặt ở `src/app/globals.css` (`@page size: 13.333in 7.5in`).
