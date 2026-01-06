import { MarkdownMath } from "@/components/MarkdownMath";
import type { ParsedSlide } from "@/lib/slides";

export function Slide({
  docTitle,
  slide,
  showAnswers,
  variant,
}: {
  docTitle?: string;
  slide: ParsedSlide;
  showAnswers: boolean;
  variant: "screen" | "print";
}) {
  const isPrint = variant === "print";

  return (
    <section
      className={
        isPrint
          ? "print-slide flex flex-col bg-white"
          : "slide flex flex-col bg-white shadow-sm"
      }
    >
      <header
        className={
          isPrint
            ? "flex items-center justify-between px-10 pt-8"
            : "flex items-center justify-between px-8 pt-6"
        }
      >
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            {slide.typeLabel}
          </div>
          <div className="truncate text-sm font-medium text-zinc-800">
            {docTitle ?? "Tài liệu"}
          </div>
        </div>
        <div className="shrink-0 text-xs font-semibold text-zinc-500">
          Slide {slide.index}
        </div>
      </header>

      <div className={isPrint ? "px-10 pt-6 pb-8" : "px-8 pt-5 pb-7"}>
        <MarkdownMath markdown={slide.bodyMarkdown || "_(trống)_" } />

        {showAnswers && slide.answerMarkdown ? (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-950">
            <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Đáp án
            </div>
            <MarkdownMath markdown={slide.answerMarkdown} className="text-[0.98em]" />
          </div>
        ) : null}
      </div>
    </section>
  );
}

