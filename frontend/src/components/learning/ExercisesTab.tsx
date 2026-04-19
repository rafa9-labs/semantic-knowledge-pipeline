"use client";

import { useState } from "react";
import { getExerciseTypeColor, getDifficultyColor } from "@/lib/colors";

interface Exercise {
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
}

interface ExercisesTabProps {
  exercises: Exercise[];
}

function PredictOutputExercise({ exercise }: { exercise: Exercise }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const tc = getExerciseTypeColor("predict_output");

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-3 bg-muted/50 border-b border-border">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-medium">{exercise.title}</h3>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${tc.bg} ${tc.text} ${tc.border}`}>
              {tc.label}
            </span>
            <span className="rounded-full bg-background border border-border px-2 py-0.5 text-xs font-mono text-muted-foreground">
              {exercise.language}
            </span>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{exercise.description}</p>
      </div>

      <pre className="p-4 overflow-x-auto text-sm bg-zinc-900">
        <code>{exercise.solution_code}</code>
      </pre>

      {exercise.options && (
        <div className="px-4 py-3 space-y-2">
          <p className="text-xs font-medium text-muted-foreground mb-2">Select your answer:</p>
          {exercise.options.map((opt, i) => {
            const isCorrect = opt.is_correct;
            const isSelected = selected === opt.label;
            let optClass = "border-border bg-background hover:border-primary/50";
            if (revealed && isCorrect) optClass = "border-emerald-400/50 bg-emerald-400/10";
            if (revealed && isSelected && !isCorrect) optClass = "border-rose-400/50 bg-rose-400/10";
            if (!revealed && isSelected) optClass = "border-primary bg-primary/10";

            return (
              <button
                key={i}
                onClick={() => { if (!revealed) setSelected(opt.label); }}
                className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ${optClass}`}
              >
                <span className="font-mono mr-2 text-muted-foreground">{String.fromCharCode(65 + i)}.</span>
                {opt.label}
                {revealed && isCorrect && <span className="ml-2 text-emerald-400">✓</span>}
                {revealed && isSelected && !isCorrect && <span className="ml-2 text-rose-400">✗</span>}
              </button>
            );
          })}
          <button
            onClick={() => setRevealed(true)}
            className="text-xs text-primary hover:text-primary/80 transition-colors mt-2"
          >
            {revealed ? "Answer revealed" : "Check answer"}
          </button>
        </div>
      )}

      {exercise.learning_objectives.length > 0 && (
        <div className="px-4 py-3 border-t border-border">
          <div className="flex flex-wrap gap-1">
            {exercise.learning_objectives.map((obj, i) => (
              <span key={i} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{obj}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FixBugExercise({ exercise }: { exercise: Exercise }) {
  const [showHint, setShowHint] = useState(0);
  const [showFix, setShowFix] = useState(false);
  const tc = getExerciseTypeColor("fix_bug");

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-3 bg-muted/50 border-b border-border">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-medium">{exercise.title}</h3>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${tc.bg} ${tc.text} ${tc.border}`}>
              {tc.label}
            </span>
            <span className="rounded-full bg-background border border-border px-2 py-0.5 text-xs font-mono text-muted-foreground">
              {exercise.language}
            </span>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{exercise.description}</p>
      </div>

      <div className="border-b border-border">
        <div className="px-4 py-2 text-xs text-rose-400 font-medium border-b border-border bg-rose-400/5">
          Buggy Code
        </div>
        <pre className="p-4 overflow-x-auto text-sm bg-zinc-900">
          <code>{exercise.buggy_code || exercise.starter_code}</code>
        </pre>
      </div>

      {exercise.hints.length > 0 && (
        <div className="border-b border-border px-4 py-3">
          {showHint > 0 && (
            <div className="space-y-2 mb-2">
              {exercise.hints.slice(0, showHint).map((hint, i) => (
                <div key={i} className="flex gap-2 text-sm">
                  <span className="text-yellow-500 shrink-0">Hint {i + 1}:</span>
                  <span className="text-muted-foreground">{hint}</span>
                </div>
              ))}
            </div>
          )}
          {showHint < exercise.hints.length ? (
            <button
              onClick={() => setShowHint(showHint + 1)}
              className="text-xs text-yellow-500 hover:text-yellow-400 transition-colors"
            >
              Reveal hint ({showHint}/{exercise.hints.length})
            </button>
          ) : (
            <p className="text-xs text-muted-foreground">All hints revealed</p>
          )}
        </div>
      )}

      <div className="px-4 py-3">
        <button
          onClick={() => setShowFix(!showFix)}
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          {showFix ? "Hide fix" : "Show fix"}
        </button>
        {showFix && (
          <>
            <pre className="mt-3 p-4 overflow-x-auto text-sm bg-zinc-900 rounded-lg border border-border">
              <code>{exercise.solution_code}</code>
            </pre>
            {exercise.bug_explanation && (
              <div className="mt-3 rounded-lg border border-emerald-400/30 bg-emerald-400/5 p-3">
                <p className="text-xs font-medium text-emerald-400 mb-1">What was wrong:</p>
                <p className="text-sm text-muted-foreground">{exercise.bug_explanation}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function BuildFromSpecExercise({ exercise }: { exercise: Exercise }) {
  const [visibleHints, setVisibleHints] = useState(0);
  const [showSolution, setShowSolution] = useState(false);
  const tc = getExerciseTypeColor("build_from_spec");
  const diff = getDifficultyColor(exercise.difficulty);

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-3 bg-muted/50 border-b border-border">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-medium">{exercise.title}</h3>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${tc.bg} ${tc.text} ${tc.border}`}>
              {tc.label}
            </span>
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className={`h-1 w-3 rounded-full ${i < exercise.difficulty ? diff.bar : "bg-muted"}`} />
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

      {exercise.hints.length > 0 && (
        <div className="border-b border-border px-4 py-3">
          {visibleHints > 0 && (
            <div className="space-y-2 mb-2">
              {exercise.hints.slice(0, visibleHints).map((hint, i) => (
                <div key={i} className="flex gap-2 text-sm">
                  <span className="text-yellow-500 shrink-0">Hint {i + 1}:</span>
                  <span className="text-muted-foreground">{hint}</span>
                </div>
              ))}
            </div>
          )}
          {visibleHints < exercise.hints.length ? (
            <button
              onClick={() => setVisibleHints(visibleHints + 1)}
              className="text-xs text-yellow-500 hover:text-yellow-400 transition-colors"
            >
              Reveal hint ({visibleHints}/{exercise.hints.length})
            </button>
          ) : (
            <p className="text-xs text-muted-foreground">All hints revealed</p>
          )}
        </div>
      )}

      <div className="px-4 py-3">
        <button
          onClick={() => setShowSolution(!showSolution)}
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          {showSolution ? "Hide solution" : "Show solution"}
        </button>
        {showSolution && (
          <pre className="mt-3 p-4 overflow-x-auto text-sm bg-zinc-900 rounded-lg border border-border">
            <code>{exercise.solution_code}</code>
          </pre>
        )}
      </div>

      {exercise.learning_objectives.length > 0 && (
        <div className="px-4 py-3 border-t border-border">
          <div className="flex flex-wrap gap-1">
            {exercise.learning_objectives.map((obj, i) => (
              <span key={i} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{obj}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ExercisesTab({ exercises }: ExercisesTabProps) {
  if (!exercises || exercises.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No exercises available for this concept yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">Practice Exercises</h2>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          {exercises.length}
        </span>
      </div>

      {exercises.map((exercise) => {
        switch (exercise.exercise_type) {
          case "predict_output":
            return <PredictOutputExercise key={exercise.id} exercise={exercise} />;
          case "fix_bug":
            return <FixBugExercise key={exercise.id} exercise={exercise} />;
          case "build_from_spec":
          default:
            return <BuildFromSpecExercise key={exercise.id} exercise={exercise} />;
        }
      })}
    </div>
  );
}
