"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface TheoryTabProps {
  theoryText: string | null;
  keyPoints: string[];
  commonMistakes: string[];
}

export function TheoryTab({ theoryText, keyPoints, commonMistakes }: TheoryTabProps) {
  if (!theoryText) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">Theory content not yet available for this concept.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="prose prose-invert max-w-none prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-border prose-code:text-primary">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {theoryText}
        </ReactMarkdown>
      </div>

      {keyPoints && keyPoints.length > 0 && (
        <div className="rounded-xl border border-border p-6">
          <h3 className="text-sm font-semibold text-primary mb-3">Key Points</h3>
          <ul className="space-y-2">
            {keyPoints.map((point, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                <span className="text-primary mt-0.5">&#x2022;</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {commonMistakes && commonMistakes.length > 0 && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6">
          <h3 className="text-sm font-semibold text-destructive mb-3">Common Mistakes</h3>
          <ul className="space-y-2">
            {commonMistakes.map((mistake, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                <span className="text-destructive mt-0.5">&#x26A0;</span>
                <span>{mistake}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
