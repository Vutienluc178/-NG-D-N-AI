"use client";

import { Slide } from "@/components/Slide";
import { parseSource } from "@/lib/slides";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

const STORAGE_KEY = "latexQuizSource_v1";

export function PrintClient() {
  const sp = useSearchParams();
  const showAnswers = (sp.get("answers") ?? "1") === "1";

  const [source] = useState<string>(() => {
    try {
      if (typeof window === "undefined") return "";
      return window.localStorage.getItem(STORAGE_KEY) ?? "";
    } catch {
      return "";
    }
  });

  const parsed = useMemo(() => parseSource(source), [source]);

  return (
    <div className="bg-white text-zinc-950">
      <div className="no-print sticky top-0 z-10 border-b border-zinc-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold">Xuất PDF (Print)</div>
            <div className="truncate text-xs text-zinc-600">
              Gợi ý: chọn <b>Scale: 100%</b>, bỏ <b>Headers and footers</b> nếu
              có.
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Link
              href="/"
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold hover:bg-zinc-50"
            >
              ← Quay lại
            </Link>
            <button
              className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800"
              onClick={() => window.print()}
            >
              In / Lưu PDF
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 px-4 py-6">
        {parsed.slides.map((s) => (
          <Slide
            key={s.id}
            docTitle={parsed.title}
            slide={s}
            showAnswers={showAnswers}
            variant="print"
          />
        ))}
      </div>
    </div>
  );
}

