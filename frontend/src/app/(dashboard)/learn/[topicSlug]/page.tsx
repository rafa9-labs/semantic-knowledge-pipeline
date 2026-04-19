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

const categoryIcon: Record<string, string> = {
  language_feature: "{ }",
  framework: "< />",
  tool: "[ ]",
  pattern: "* *",
  concept: "(i)",
};

const difficultyColor: Record<string, string> = {
  beginner: "bg-green-500/10 text-green-400 border-green-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default async function TopicPage({ params }: { params: Promise<{ topicSlug: string }> }) {
  const { topicSlug } = await params;
  const topic = await getTopic(topicSlug);

  if (!topic) {
    return (
      <div>
        <h1 className="text-2xl font-bold">Topic Not Found</h1>
        <p className="mt-2 text-muted-foreground">Could not find &quot;{topicSlug}&quot;.</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        {topic.domain_name && (
          <p className="text-sm text-muted-foreground mb-1">{topic.domain_name}</p>
        )}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{topic.name}</h1>
          {topic.difficulty && (
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${difficultyColor[topic.difficulty] || ""}`}>
              {topic.difficulty}
            </span>
          )}
        </div>
        <p className="mt-2 text-muted-foreground">{topic.description}</p>
        <p className="mt-2 text-sm">
          <span className="text-primary font-medium">{topic.concepts.length} concepts</span>
          <span className="text-muted-foreground"> to learn</span>
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {topic.concepts.map((concept) => (
          <Link
            key={concept.id}
            href={`/learn/${topicSlug}/concept/${concept.slug}`}
            className="group flex items-center gap-3 rounded-lg border border-border p-4 hover:border-primary/50 transition-colors"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-xs text-muted-foreground">
              {categoryIcon[concept.category] || "?"}
            </span>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium group-hover:text-primary transition-colors truncate">
                {concept.name}
              </h3>
              <div className="flex gap-2 mt-0.5">
                <span className="text-xs text-muted-foreground capitalize">{concept.category.replace(/_/g, " ")}</span>
                {concept.has_theory && <span className="text-xs text-muted-foreground">theory</span>}
                {concept.has_eli5 && <span className="text-xs text-muted-foreground">ELI5</span>}
              </div>
            </div>
            <div className="flex gap-0.5 shrink-0">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 w-3 rounded-full ${i < concept.difficulty ? "bg-primary" : "bg-muted"}`}
                />
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
