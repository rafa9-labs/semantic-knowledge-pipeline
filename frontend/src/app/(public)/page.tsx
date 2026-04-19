export default function LandingPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          Master any subject through{" "}
          <span className="text-primary">AI-powered knowledge graphs</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground">
          KodaStudy generates structured curricula on-demand using AI.
          Learn through simple explanations, interactive code examples, and an AI tutor
          that understands what you&apos;re studying.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <a
            href="/catalog"
            className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            Browse Topics
          </a>
          <a
            href="/signup"
            className="rounded-lg border border-border px-6 py-3 font-medium hover:bg-accent transition-colors"
          >
            Get Started Free
          </a>
        </div>
      </div>
    </div>
  );
}
