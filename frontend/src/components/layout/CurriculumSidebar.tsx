"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getCategoryColor } from "@/lib/colors";

interface Topic {
  id: number;
  name: string;
  slug: string;
  domain_name: string | null;
  domain_slug: string | null;
  concept_count: number;
}

interface ConceptItem {
  id: number;
  name: string;
  slug: string;
  category: string;
  difficulty: number;
}

const categoryIcons: Record<string, string> = {
  language_feature: "{ }",
  framework: "< />",
  tool: "[ ]",
  pattern: "* *",
  concept: "(i)",
};

function categoryDotClass(category: string): string {
  const c = getCategoryColor(category);
  return `${c.dot} w-1.5 h-1.5 rounded-full shrink-0`;
}

export function CurriculumSidebar() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null);
  const [concepts, setConcepts] = useState<ConceptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiBase}/api/knowledge/topics`)
      .then((res) => res.json())
      .then((data) => {
        setTopics(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    const match = pathname.match(/\/learn\/([^/]+)/);
    if (match) {
      const topicSlug = match[1];
      setExpandedTopic(topicSlug);
      const topic = topics.find((t) => t.slug === topicSlug);
      if (topic?.domain_slug) {
        setExpandedDomain(topic.domain_slug);
      }
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      fetch(`${apiBase}/api/knowledge/topics/${topicSlug}`)
        .then((res) => res.json())
        .then((data) => {
          setConcepts(data.concepts || []);
        })
        .catch(() => {});
    }
  }, [pathname, topics]);

  const activeConceptSlug = pathname.match(/\/concept\/([^/]+)/)?.[1] || null;

  const grouped = topics.reduce<Record<string, { slug: string; topics: Topic[] }>>((acc, topic) => {
    const domain = topic.domain_name || "Other";
    if (!acc[domain]) {
      acc[domain] = { slug: topic.domain_slug || "other", topics: [] };
    }
    acc[domain].topics.push(topic);
    return acc;
  }, {});

  return (
    <aside className="flex h-full flex-col border-r border-border bg-card overflow-y-auto">
      <div className="p-4 border-b border-border">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Curriculum</h2>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        <Link
          href="/dashboard"
          className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
            pathname === "/dashboard"
              ? "bg-accent text-foreground font-medium"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          Dashboard
        </Link>

        {loading ? (
          <div className="px-3 py-4 space-y-2">
            <div className="h-3 bg-muted rounded w-3/4 animate-pulse" />
            <div className="h-3 bg-muted rounded w-1/2 animate-pulse" />
          </div>
        ) : (
          Object.entries(grouped).map(([domainName, group]) => (
            <div key={domainName} className="mt-2">
              <button
                onClick={() => setExpandedDomain(expandedDomain === group.slug ? null : group.slug)}
                className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
              >
                <span>{domainName}</span>
                <span className="text-[10px]">{expandedDomain === group.slug ? "▼" : "▶"}</span>
              </button>

              {expandedDomain === group.slug && (
                <div className="mt-1 space-y-0.5">
                  {group.topics.map((topic) => (
                    <div key={topic.id}>
                      <Link
                        href={`/learn/${topic.slug}`}
                        className={`flex items-center justify-between rounded-lg px-3 py-1.5 text-sm transition-colors ${
                          expandedTopic === topic.slug
                            ? "bg-accent text-foreground font-medium"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        }`}
                      >
                        <span className="truncate">{topic.name}</span>
                        <span className="text-xs text-muted-foreground ml-1 shrink-0">{topic.concept_count}</span>
                      </Link>

                      {expandedTopic === topic.slug && concepts.length > 0 && (
                        <div className="ml-3 mt-0.5 space-y-0.5 border-l border-border pl-2">
                          {concepts.map((concept) => (
                            <Link
                              key={concept.id}
                              href={`/learn/${topic.slug}/concept/${concept.slug}`}
                              className={`flex items-center gap-2 rounded-md px-2 py-1 text-xs transition-colors ${
                                activeConceptSlug === concept.slug
                                  ? "bg-primary/10 text-primary font-medium"
                                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
                              }`}
                            >
                              <span className={categoryDotClass(concept.category)} />
                              <span className="truncate">{concept.name}</span>
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </nav>
    </aside>
  );
}
