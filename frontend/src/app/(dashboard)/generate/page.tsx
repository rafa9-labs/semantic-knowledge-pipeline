export default function GeneratePage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Generate a New Curriculum</h1>
      <p className="mt-2 text-muted-foreground">Tell us what you want to learn and we&apos;ll generate a complete curriculum.</p>
      <div className="mt-8 space-y-4">
        <input
          type="text"
          placeholder="e.g. Rust Programming, Quantum Computing, Spanish Grammar"
          className="w-full rounded-lg border border-border bg-background px-4 py-3 text-sm"
        />
        <button className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
          Generate Curriculum
        </button>
      </div>
    </div>
  );
}
