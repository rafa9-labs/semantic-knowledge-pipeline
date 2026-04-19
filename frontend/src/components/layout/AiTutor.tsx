"use client";

import { useState } from "react";

export function AiTutor() {
  const [input, setInput] = useState("");

  return (
    <aside className="flex h-full flex-col border-l border-border bg-card">
      <div className="p-4 border-b border-border">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">AI Tutor</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <p className="text-sm text-muted-foreground">Ask questions about what you&apos;re learning.</p>
      </div>
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <button className="rounded-lg bg-primary px-3 py-2 text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
            Send
          </button>
        </div>
      </div>
    </aside>
  );
}
