const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export const api = {
  getDomains: () => apiFetch<{ id: number; name: string; slug: string; topic_count: number }[]>("/api/knowledge/domains"),
  getTopics: () => apiFetch<{ id: number; name: string; slug: string; concept_count: number }[]>("/api/knowledge/topics"),
  getTopic: (slug: string) => apiFetch<any>(`/api/knowledge/topics/${slug}`),
  getConcept: (slug: string) => apiFetch<any>(`/api/knowledge/concepts/${slug}`),
  chat: (message: string, conceptId?: number) =>
    apiFetch<{ answer: string; citations: any[] }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, concept_id: conceptId }),
    }),
};