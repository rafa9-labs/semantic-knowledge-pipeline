interface Eli5TabProps {
  simpleExplanation: string | null;
  keyPoints: string[];
}

export function Eli5Tab({ simpleExplanation, keyPoints }: Eli5TabProps) {
  if (!simpleExplanation) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">ELI5 explanation not yet available for this concept.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-primary/30 bg-primary/5 p-6">
        <h3 className="text-sm font-semibold text-primary mb-3">Explain Like I&apos;m 5</h3>
        <p className="text-foreground leading-relaxed whitespace-pre-wrap">{simpleExplanation}</p>
      </div>

      {keyPoints && keyPoints.length > 0 && (
        <div className="rounded-xl border border-border p-6">
          <h3 className="text-sm font-semibold text-primary mb-3">Key Takeaways</h3>
          <ul className="space-y-2">
            {keyPoints.map((point, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <span className="text-primary font-bold">{i + 1}.</span>
                <span className="text-muted-foreground">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
