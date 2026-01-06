import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

export function MarkdownMath({
  markdown,
  className,
}: {
  markdown: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-3xl font-semibold tracking-tight">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-2xl font-semibold tracking-tight">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xl font-semibold tracking-tight">{children}</h3>
          ),
          p: ({ children }) => <p className="mt-3 leading-relaxed">{children}</p>,
          ul: ({ children }) => (
            <ul className="mt-3 list-disc pl-6 leading-relaxed">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mt-3 list-decimal pl-6 leading-relaxed">{children}</ol>
          ),
          li: ({ children }) => <li className="mt-1">{children}</li>,
          code: ({ children }) => (
            <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[0.95em] text-zinc-800">
              {children}
            </code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mt-3 border-l-4 border-zinc-200 pl-4 text-zinc-700">
              {children}
            </blockquote>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

