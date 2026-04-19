"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { TheoryTab } from "@/components/learning/TheoryTab";
import { Eli5Tab } from "@/components/learning/Eli5Tab";
import { ExamplesTab } from "@/components/learning/ExamplesTab";
import { ExercisesTab } from "@/components/learning/ExercisesTab";
import { getCategoryColor, getDifficultyColor } from "@/lib/colors";

interface ConceptData {
  id: number;
  name: string;
  slug: string;
  category: string;
  difficulty: number;
  theory_text: string | null;
  simple_explanation: string | null;
  key_points: string[];
  common_mistakes: string[];
  topic_name: string | null;
  topic_slug: string | null;
  examples: {
    id: number;
    title: string;
    description: string | null;
    code: string;
    language: string;
    explanation: string | null;
    source_type: string;
    when_to_use: string | null;
    difficulty_level: number | null;
  }[];
  exercises: {
    id: number;
    title: string;
    description: string;
    difficulty: number;
    language: string;
    exercise_type: string;
    starter_code: string | null;
    solution_code: string;
    hints: string[];
    test_cases: { input: string; expected: string }[];
    learning_objectives: string[];
    options: { label: string; is_correct: boolean }[] | null;
    correct_answer: string | null;
    buggy_code: string | null;
    bug_explanation: string | null;
  }[];
  relationships: {
    outgoing: { id: number; name: string; slug: string; type: string }[];
    incoming: { id: number; name: string; slug: string; type: string }[];
  };
}

const tabs = ["Theory", "ELI5", "Examples", "Exercises"] as const;
type Tab = (typeof tabs)[number];

const tabCounts = (data: ConceptData): Record<Tab, number | null> => ({
  Theory: data.theory_text ? 1 : 0,
  ELI5: data.simple_explanation ? 1 : 0,
  Examples: data.examples.length,
  Exercises: data.exercises.length,
});

export default function ConceptPage() {
  const { topicSlug, conceptSlug } = useParams<{ topicSlug: string; conceptSlug: string }>();
  const [data, setData] = useState<ConceptData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Theory");

  useEffect(() => {
    if (!topicSlug || !conceptSlug) return;
    setLoading(true);
    setError(null);
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiBase}/api/knowledge/concepts/slug/${topicSlug}/${conceptSlug}`)
      .then((res) => {
        if (!res.ok) throw new Error("Concept not found");
        return res.json();
      })
      .then((data) => {
        setData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [topicSlug, conceptSlug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="space-y-3 w-full max-w-lg">
          <div className="h-6 bg-muted rounded w-1/3 animate-pulse" />
          <div className="h-4 bg-muted rounded w-2/3 animate-pulse" />
          <div className="h-40 bg-muted rounded animate-pulse mt-6" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <h2 className="text-lg font-semibold">Concept Not Found</h2>
        <p className="mt-2 text-muted-foreground">{error || "Could not load concept data."}</p>
      </div>
    );
  }

  const counts = tabCounts(data);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${getCategoryColor(data.category).bg} ${getCategoryColor(data.category).text} ${getCategoryColor(data.category).border}`}>
            {getCategoryColor(data.category).label}
          </span>
        </div>
        <h1 className="text-xl font-bold">{data.name}</h1>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex gap-0.5">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className={`h-1 w-4 rounded-full ${i < data.difficulty ? getDifficultyColor(data.difficulty).bar : "bg-muted"}`}
              />
            ))}
          </div>
          <span className="text-xs text-muted-foreground">{getDifficultyColor(data.difficulty).label}</span>
        </div>
      </div>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === tab
                ? "border-b-2 border-primary text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
            {counts[tab] !== null && counts[tab] > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] leading-none">
                {counts[tab]}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        {activeTab === "Theory" && (
          <TheoryTab
            theoryText={data.theory_text}
            keyPoints={data.key_points}
            commonMistakes={data.common_mistakes}
          />
        )}
        {activeTab === "ELI5" && (
          <Eli5Tab
            simpleExplanation={data.simple_explanation}
            keyPoints={data.key_points}
          />
        )}
        {activeTab === "Examples" && <ExamplesTab examples={data.examples} />}
        {activeTab === "Exercises" && <ExercisesTab exercises={data.exercises} />}
      </div>
    </div>
  );
}
