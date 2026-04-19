"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface Example {
  id: number;
  title: string;
  description: string | null;
  code: string;
  language: string;
  explanation: string | null;
  source_type: string;
}

interface ExamplesTabProps {
  examples: Example[];
}

export function ExamplesTab({ examples }: ExamplesTabProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const codeBlock = (lang: string, code: string) => {
    const bt = String.fromCharCode(96);
    return `${bt}${bt}${bt}${lang}\n${code}\n${bt}${bt}${bt}`;
  };

  if (!examples || examples.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No code examples available for this concept yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">Code Examples</h2>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          {examples.length}
        </span>
      </div>

      {examples.map((example) => (
        <div key={example.id} className="rounded-xl border border-border overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-muted/50 border-b border-border">
            <div>
              <h3 className="text-sm font-medium">{example.title}</h3>
              {example.description && (
                <p className="text-xs text-muted-foreground mt-0.5">{example.description}</p>
              )}
            </div>
            <span className="rounded-full bg-background border border-border px-2 py-0.5 text-xs font-mono text-muted-foreground">
              {example.language}
            </span>
          </div>

          <div className="overflow-x-auto">
            <div className="prose prose-invert prose-pre:bg-zinc-900 prose-pre:m-0 prose-pre:rounded-none prose-pre:border-0 prose-pre:p-4 prose-code:text-primary max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {codeBlock(example.language, example.code)}
              </ReactMarkdown>
            </div>
          </div>

          {example.explanation && (
            <div className="border-t border-border">
              <button
                onClick={() => setExpandedId(expandedId === example.id ? null : example.id)}
                className="w-full px-4 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors text-left"
              >
                {expandedId === example.id ? "Hide explanation" : "Show explanation"}
              </button>
              {expandedId === example.id && (
                <div className="px-4 pb-4 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                  {example.explanation}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
