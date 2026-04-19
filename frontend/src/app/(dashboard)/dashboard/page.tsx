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

export default async function DashboardPage() {
  const topics = await getTopics();

  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-1 text-muted-foreground">Choose a topic to start learning.</p>

      {topics.length === 0 ? (
        <div className="mt-8 rounded-xl border border-border p-12 text-center">
          <p className="text-muted-foreground">No topics found. Make sure FastAPI is running on port 8000.</p>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {topics.map((topic) => (
            <Link
              key={topic.id}
              href={`/learn/${topic.slug}`}
              className="group rounded-xl border border-border p-5 hover:border-primary/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold group-hover:text-primary transition-colors">{topic.name}</h3>
                  {topic.domain_name && (
                    <p className="text-xs text-muted-foreground mt-0.5">{topic.domain_name}</p>
                  )}
                </div>
                {topic.difficulty && (
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${difficultyColor[topic.difficulty] || ""}`}>
                    {topic.difficulty}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{topic.description}</p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  {topic.concept_count} concept{topic.concept_count !== 1 ? "s" : ""}
                </span>
                <span className="text-xs text-muted-foreground group-hover:text-primary transition-colors">
                  Start Learning &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
