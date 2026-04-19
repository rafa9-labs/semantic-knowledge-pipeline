import Link from "next/link";

interface Topic {
  id: number;
  name: string;
  slug: string;
  description: string;
  difficulty: string;
  concept_count: number;
  domain_name: string | null;
  domain_slug: string | null;
}

async function getTopics(): Promise<Topic[]> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/knowledge/topics`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

const difficultyColor: Record<string, string> = {
  beginner: "bg-green-500/10 text-green-400 border-green-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default async function CatalogPage() {
  const topics = await getTopics();

  return (
    <div className="mx-auto max-w-7xl px-6 py-24">
      <h1 className="text-4xl font-bold">Topic Catalog</h1>
      <p className="mt-2 text-muted-foreground text-lg">
        Browse all available learning topics. Each topic contains structured concepts with theory, explanations, code examples, and exercises.
      </p>

      {topics.length === 0 ? (
        <div className="mt-12 rounded-xl border border-border p-12 text-center">
          <p className="text-muted-foreground">No topics found. Make sure FastAPI is running on port 8000.</p>
        </div>
      ) : (
        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map((topic) => (
            <Link
              key={topic.id}
              href={`/topic/${topic.slug}`}
              className="group rounded-xl border border-border p-6 hover:border-primary/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold group-hover:text-primary transition-colors">{topic.name}</h3>
                {topic.difficulty && (
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${difficultyColor[topic.difficulty] || difficultyColor.intermediate}`}>
                    {topic.difficulty}
                  </span>
                )}
              </div>
              {topic.domain_name && (
                <p className="mt-1 text-xs text-muted-foreground">{topic.domain_name}</p>
              )}
              <p className="mt-3 text-sm text-muted-foreground line-clamp-2">{topic.description}</p>
              <p className="mt-4 text-sm font-medium text-primary">
                {topic.concept_count} concept{topic.concept_count !== 1 ? "s" : ""}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
