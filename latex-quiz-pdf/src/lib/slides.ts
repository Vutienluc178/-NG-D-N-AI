export type SlideType = "mc" | "tf" | "sa" | "slide";

export type ParsedSlide = {
  id: string;
  index: number;
  type: SlideType;
  typeLabel: string;
  bodyMarkdown: string;
  answerMarkdown?: string;
};

const TYPE_LABEL: Record<SlideType, string> = {
  mc: "Trắc nghiệm",
  tf: "Đúng / Sai",
  sa: "Trả lời ngắn",
  slide: "Nội dung",
};

function normalizeNewlines(input: string) {
  return input.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function extractDocTitle(source: string): string | undefined {
  const m = normalizeNewlines(source).match(/^\s*#\s+(.+)\s*$/m);
  return m?.[1]?.trim() || undefined;
}

function splitBySlideBreaks(source: string): string[] {
  // Slide break is a line that is exactly: ---
  return normalizeNewlines(source)
    .split(/^\s*---\s*$/m)
    .map((s) => s.trim())
    .filter(Boolean);
}

function extractTypeTag(chunk: string): { type: SlideType; rest: string } {
  const lines = normalizeNewlines(chunk).split("\n");
  const firstNonEmptyIdx = lines.findIndex((l) => l.trim().length > 0);
  if (firstNonEmptyIdx < 0) return { type: "slide", rest: "" };

  const first = lines[firstNonEmptyIdx].trim();
  const type =
    first.toUpperCase() === "[MC]"
      ? "mc"
      : first.toUpperCase() === "[TF]"
        ? "tf"
        : first.toUpperCase() === "[SA]"
          ? "sa"
          : "slide";

  if (type === "slide") return { type, rest: chunk.trim() };

  const restLines = [...lines];
  restLines.splice(firstNonEmptyIdx, 1);
  return { type, rest: restLines.join("\n").trim() };
}

function extractAnswer(rest: string): { body: string; answer?: string } {
  let body = normalizeNewlines(rest);

  // Block form:
  // :::answer
  // ...markdown...
  // :::
  const block = body.match(/^\s*:::answer\s*\n([\s\S]*?)\n:::\s*$/im);
  if (block?.[1]) {
    const answer = block[1].trim();
    body = body.replace(block[0], "").trim();
    return { body, answer: answer || undefined };
  }

  // Single-line forms:
  // **Đáp án:** ...
  // Đáp án: ...
  const lines = body.split("\n");
  let answer: string | undefined;
  const kept: string[] = [];
  for (const line of lines) {
    if (answer === undefined) {
      const m = line.match(/^\s*(\*\*Đáp án:\*\*|Đáp án:)\s*(.*)\s*$/i);
      if (m && typeof m[2] === "string") {
        const a = m[2].trim();
        answer = a.length ? a : undefined;
        continue;
      }
    }
    kept.push(line);
  }

  return { body: kept.join("\n").trim(), answer };
}

export function parseSource(source: string): {
  title?: string;
  slides: ParsedSlide[];
} {
  const title = extractDocTitle(source);
  const chunks = splitBySlideBreaks(source);

  const slides: ParsedSlide[] = chunks.map((chunk, idx) => {
    const { type, rest } = extractTypeTag(chunk);
    const { body, answer } = extractAnswer(rest);
    const typeLabel = TYPE_LABEL[type];

    return {
      id: `slide_${idx + 1}`,
      index: idx + 1,
      type,
      typeLabel,
      bodyMarkdown: body,
      answerMarkdown: answer,
    };
  });

  return { title, slides };
}

