import Link from "next/link";

interface Concept {
  id: number;
  name: string;
  slug: string;
  category: string;
  difficulty: number;
  has_eli5: boolean;
  has_theory: boolean;
}

interface TopicData {
  id: number;
  name: string;
  slug: string;
  description: string;
  difficulty: string;
  domain_name: string | null;
  domain_slug: string | null;
  concepts: Concept[];
}

async function getTopic(slug: string): Promise<TopicData | null> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/knowledge/topics/${slug}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function TopicPreviewPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = await getTopic(slug);

  if (!topic) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-24">
        <h1 className="text-4xl font-bold">Topic Not Found</h1>
        <p className="mt-2 text-muted-foreground">Could not find a topic with slug &quot;{slug}&quot;.</p>
        <Link href="/catalog" className="mt-4 inline-block text-primary hover:underline">Back to Catalog</Link>
      </div>
    );
  }

  const categoryIcon: Record<string, string> = {
    language_feature: "{ }",
    framework: "< />",
    tool: "[ ]",
    pattern: "* *",
    concept: "(i)",
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-24">
      <Link href="/catalog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        &larr; Back to Catalog
      </Link>
      <div className="mt-4">
        {topic.domain_name && (
          <p className="text-sm text-muted-foreground">{topic.domain_name}</p>
        )}
        <h1 className="text-4xl font-bold">{topic.name}</h1>
        <p className="mt-2 text-muted-foreground">{topic.description}</p>
        <p className="mt-4 text-sm">
          <span className="text-primary font-medium">{topic.concepts.length} concepts</span>
          <span className="text-muted-foreground"> available to learn</span>
        </p>
      </div>

      <div className="mt-12 space-y-3">
        {topic.concepts.map((concept) => (
          <Link
            key={concept.id}
            href={`/learn/${topic.slug}/concept/${concept.slug}`}
            className="group flex items-center gap-4 rounded-lg border border-border p-4 hover:border-primary/50 transition-colors"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-xs text-muted-foreground">
              {categoryIcon[concept.category] || "?"}
            </span>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium group-hover:text-primary transition-colors">{concept.name}</h3>
              <div className="flex gap-2 mt-1">
                <span className="text-xs text-muted-foreground">{concept.category.replace("_", " ")}</span>
                {concept.has_theory && <span className="text-xs text-muted-foreground">&middot; theory</span>}
                {concept.has_eli5 && <span className="text-xs text-muted-foreground">&middot; ELI5</span>}
              </div>
            </div>
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1.5 w-4 rounded-full ${i < concept.difficulty ? "bg-primary" : "bg-muted"}`}
                />
              ))}
            </div>
          </Link>
        ))}
      </div>

      {topic.concepts.length > 0 && (
        <div className="mt-8">
          <Link
            href={`/learn/${topic.slug}`}
            className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            Start Learning
          </Link>
        </div>
      )}
    </div>
  );
}
