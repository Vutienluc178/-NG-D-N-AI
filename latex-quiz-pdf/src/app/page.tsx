"use client";

import { Slide } from "@/components/Slide";
import { parseSource } from "@/lib/slides";
import { useEffect, useMemo, useRef, useState } from "react";

const STORAGE_KEY = "latexQuizSource_v1";

const DEFAULT_SOURCE = `# Đề ôn tập Toán (LaTeX)

> Mẹo: dùng $...$ cho công thức inline và $$...$$ cho công thức riêng dòng.
> Tách slide bằng một dòng chỉ có: ---

---

[MC]
Cho phương trình $x^2 - 1 = 0$. Nghiệm của phương trình là:

- A. $0$
- B. $\\pm 1$
- C. $1$
- D. $-1$

**Đáp án:** B

---

[TF]
Mệnh đề: "$\\pi$ là số hữu tỉ".

**Đáp án:** Sai

---

[SA]
Tính đạo hàm của hàm số $f(x)=x^3$.

**Đáp án:** $3x^2$
`;

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function Home() {
  const [source, setSource] = useState(() => {
    try {
      if (typeof window === "undefined") return DEFAULT_SOURCE;
      const saved = window.localStorage.getItem(STORAGE_KEY);
      return saved && saved.trim().length ? saved : DEFAULT_SOURCE;
    } catch {
      return DEFAULT_SOURCE;
    }
  });
  const [showAnswers, setShowAnswers] = useState(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, source);
    } catch {
      // ignore
    }
  }, [source]);

  const parsed = useMemo(() => parseSource(source), [source]);

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950">
      <header className="no-print sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold">LaTeX Quiz → PDF (16:9)</div>
            <div className="truncate text-xs text-zinc-600">
              Soạn câu hỏi (MC/TF/SA) + xem preview slide + in ra PDF trình chiếu
              16:9.
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <label className="flex cursor-pointer items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-2 text-xs font-medium hover:bg-zinc-50">
              <input
                type="checkbox"
                checked={showAnswers}
                onChange={(e) => setShowAnswers(e.target.checked)}
              />
              Hiện đáp án
            </label>

            <button
              className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800"
              onClick={() =>
                window.open(`/print?answers=${showAnswers ? 1 : 0}`, "_blank")
              }
            >
              Xuất PDF (mở trang in)
            </button>

            <button
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold hover:bg-zinc-50"
              onClick={() => downloadTextFile("slides.md", source)}
            >
              Tải .md
            </button>

            <button
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold hover:bg-zinc-50"
              onClick={() => fileInputRef.current?.click()}
            >
              Nhập .md
            </button>
            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept=".md,.txt,text/plain"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                const text = await f.text();
                setSource(text);
                e.target.value = "";
              }}
            />

            <button
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold hover:bg-zinc-50"
              onClick={() => setSource(DEFAULT_SOURCE)}
              title="Khôi phục mẫu"
            >
              Reset
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-2">
        <section className="no-print rounded-2xl border border-zinc-200 bg-white p-4">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">Soạn thảo (Markdown + LaTeX)</div>
              <div className="text-xs text-zinc-600">
                Tách slide bằng <code>---</code>. Chọn loại câu bằng{" "}
                <code>[MC]</code>, <code>[TF]</code>, <code>[SA]</code>.
              </div>
            </div>
            <div className="text-xs text-zinc-500">
              {parsed.slides.length} slide
            </div>
          </div>

          <textarea
            className="h-[70vh] w-full resize-none rounded-xl border border-zinc-200 bg-zinc-50 p-3 font-mono text-[13px] leading-5 outline-none focus:border-zinc-400"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            spellCheck={false}
          />
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white p-4">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">Preview slide (16:9)</div>
              <div className="text-xs text-zinc-600">
                PDF: bấm <b>Xuất PDF</b> → trình duyệt → <b>Print</b> →{" "}
                <b>Save as PDF</b>.
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            {parsed.slides.map((s) => (
              <Slide
                key={s.id}
                docTitle={parsed.title}
                slide={s}
                showAnswers={showAnswers}
                variant="screen"
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
