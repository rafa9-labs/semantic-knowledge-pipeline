"use client";

import { useState } from "react";

interface Exercise {
  id: number;
  title: string;
  description: string;
  difficulty: number;
  language: string;
  starter_code: string | null;
  solution_code: string;
  hints: string[];
  learning_objectives: string[];
}

interface ExercisesTabProps {
  exercises: Exercise[];
}

export function ExercisesTab({ exercises }: ExercisesTabProps) {
  const [visibleHints, setVisibleHints] = useState<Record<number, number>>({});
  const [showSolution, setShowSolution] = useState<Record<number, boolean>>({});

  if (!exercises || exercises.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No exercises available for this concept yet.</p>
      </div>
    );
  }

  const revealHint = (exerciseId: number) => {
    setVisibleHints((prev) => ({
      ...prev,
      [exerciseId]: (prev[exerciseId] || 0) + 1,
    }));
  };

  const toggleSolution = (exerciseId: number) => {
    setShowSolution((prev) => ({
      ...prev,
      [exerciseId]: !prev[exerciseId],
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">Practice Exercises</h2>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          {exercises.length}
        </span>
      </div>

      {exercises.map((exercise) => {
        const hintCount = visibleHints[exercise.id] || 0;
        const solutionVisible = showSolution[exercise.id] || false;

        return (
          <div key={exercise.id} className="rounded-xl border border-border overflow-hidden">
            <div className="px-4 py-3 bg-muted/50 border-b border-border">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-medium">{exercise.title}</h3>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="flex gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div
                        key={i}
                        className={`h-1 w-3 rounded-full ${i < exercise.difficulty ? "bg-primary" : "bg-muted"}`}
                      />
                    ))}
                  </div>
                  <span className="rounded-full bg-background border border-border px-2 py-0.5 text-xs font-mono text-muted-foreground">
                    {exercise.language}
                  </span>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">{exercise.description}</p>
            </div>

            {exercise.starter_code && (
              <div className="border-b border-border">
                <div className="px-4 py-2 text-xs text-muted-foreground border-b border-border bg-background/50">
                  Starter Code
                </div>
                <pre className="p-4 overflow-x-auto text-sm bg-zinc-900">
                  <code>{exercise.starter_code}</code>
                </pre>
              </div>
            )}

            {exercise.hints && exercise.hints.length > 0 && (
              <div className="border-b border-border px-4 py-3">
                {hintCount > 0 && (
                  <div className="space-y-2 mb-2">
                    {exercise.hints.slice(0, hintCount).map((hint, i) => (
                      <div key={i} className="flex gap-2 text-sm">
                        <span className="text-yellow-500 shrink-0">Hint {i + 1}:</span>
                        <span className="text-muted-foreground">{hint}</span>
                      </div>
                    ))}
                  </div>
                )}
                {hintCount < exercise.hints.length ? (
                  <button
                    onClick={() => revealHint(exercise.id)}
                    className="text-xs text-yellow-500 hover:text-yellow-400 transition-colors"
                  >
                    Reveal hint ({hintCount}/{exercise.hints.length})
                  </button>
                ) : (
                  <p className="text-xs text-muted-foreground">All hints revealed</p>
                )}
              </div>
            )}

            <div className="px-4 py-3">
              <button
                onClick={() => toggleSolution(exercise.id)}
                className="text-xs text-primary hover:text-primary/80 transition-colors"
              >
                {solutionVisible ? "Hide solution" : "Show solution"}
              </button>
              {solutionVisible && (
                <pre className="mt-3 p-4 overflow-x-auto text-sm bg-zinc-900 rounded-lg border border-border">
                  <code>{exercise.solution_code}</code>
                </pre>
              )}
            </div>

            {exercise.learning_objectives && exercise.learning_objectives.length > 0 && (
              <div className="px-4 py-3 border-t border-border">
                <p className="text-xs text-muted-foreground mb-1">Learning objectives:</p>
                <div className="flex flex-wrap gap-1">
                  {exercise.learning_objectives.map((obj, i) => (
                    <span key={i} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {obj}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
