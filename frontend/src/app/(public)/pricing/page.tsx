export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-24">
      <h1 className="text-4xl font-bold text-center">Simple Pricing</h1>
      <p className="mt-4 text-center text-muted-foreground text-lg">Start free, upgrade when you need more.</p>
      <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-2">
        <div className="rounded-xl border border-border p-8">
          <h2 className="text-2xl font-semibold">Free</h2>
          <p className="mt-2 text-muted-foreground">Get started with the basics.</p>
          <p className="mt-6 text-4xl font-bold">$0<span className="text-base font-normal text-muted-foreground">/mo</span></p>
          <ul className="mt-8 space-y-3 text-sm">
            <li>Browse all topics and concepts</li>
            <li>Theory content</li>
            <li>ELI5 explanations</li>
            <li>View knowledge graph</li>
            <li>First 2 concepts fully accessible per topic</li>
          </ul>
        </div>
        <div className="rounded-xl border border-primary p-8 relative">
          <span className="absolute -top-3 left-6 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground">Premium</span>
          <h2 className="text-2xl font-semibold">Premium</h2>
          <p className="mt-2 text-muted-foreground">Unlock the full learning experience.</p>
          <p className="mt-6 text-4xl font-bold">$9.99<span className="text-base font-normal text-muted-foreground">/mo</span></p>
          <ul className="mt-8 space-y-3 text-sm">
            <li>Everything in Free, plus:</li>
            <li>Full code examples (3+ per concept)</li>
            <li>Interactive exercises with test runner</li>
            <li>AI Tutor chat with citations</li>
            <li>Interactive knowledge graph exploration</li>
            <li>Learning path generation</li>
            <li>On-demand curriculum generation</li>
            <li>Progress tracking across all topics</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
