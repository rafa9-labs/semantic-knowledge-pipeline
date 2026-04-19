export interface ColorDef {
  bg: string;
  text: string;
  border: string;
  icon: string;
  label: string;
  dot: string;
}

export const CATEGORY_COLORS: Record<string, ColorDef> = {
  language_feature: {
    bg: "bg-sky-400/15",
    text: "text-sky-400",
    border: "border-sky-400/30",
    icon: "{ }",
    label: "Language Feature",
    dot: "bg-sky-400",
  },
  framework: {
    bg: "bg-green-400/15",
    text: "text-green-400",
    border: "border-green-400/30",
    icon: "< />",
    label: "Framework",
    dot: "bg-green-400",
  },
  tool: {
    bg: "bg-amber-400/15",
    text: "text-amber-400",
    border: "border-amber-400/30",
    icon: "[ ]",
    label: "Tool",
    dot: "bg-amber-400",
  },
  pattern: {
    bg: "bg-violet-400/15",
    text: "text-violet-400",
    border: "border-violet-400/30",
    icon: "* *",
    label: "Pattern",
    dot: "bg-violet-400",
  },
  concept: {
    bg: "bg-teal-400/15",
    text: "text-teal-400",
    border: "border-teal-400/30",
    icon: "(i)",
    label: "Concept",
    dot: "bg-teal-400",
  },
};

export interface ExerciseTypeColorDef {
  bg: string;
  text: string;
  border: string;
  label: string;
  icon: string;
}

export const EXERCISE_TYPE_COLORS: Record<string, ExerciseTypeColorDef> = {
  predict_output: {
    bg: "bg-emerald-400/15",
    text: "text-emerald-400",
    border: "border-emerald-400/30",
    label: "Predict Output",
    icon: "?",
  },
  fix_bug: {
    bg: "bg-rose-400/15",
    text: "text-rose-400",
    border: "border-rose-400/30",
    label: "Fix the Bug",
    icon: "!",
  },
  build_from_spec: {
    bg: "bg-sky-400/15",
    text: "text-sky-400",
    border: "border-sky-400/30",
    label: "Build from Spec",
    icon: "+",
  },
};

export const DIFFICULTY_COLORS: Record<number, { bar: string; label: string }> = {
  1: { bar: "bg-green-400", label: "Beginner" },
  2: { bar: "bg-green-400", label: "Beginner" },
  3: { bar: "bg-yellow-400", label: "Intermediate" },
  4: { bar: "bg-rose-400", label: "Advanced" },
  5: { bar: "bg-rose-400", label: "Advanced" },
};

export const EXAMPLE_LEVEL: Record<number, { label: string; color: string }> = {
  1: { label: "Getting Started", color: "text-green-400" },
  2: { label: "Real-World Usage", color: "text-yellow-400" },
  3: { label: "Advanced Pattern", color: "text-rose-400" },
};

export function getCategoryColor(category: string): ColorDef {
  return CATEGORY_COLORS[category] ?? CATEGORY_COLORS.concept;
}

export function getExerciseTypeColor(type: string): ExerciseTypeColorDef {
  return EXERCISE_TYPE_COLORS[type] ?? EXERCISE_TYPE_COLORS.build_from_spec;
}

export function getDifficultyColor(difficulty: number) {
  return DIFFICULTY_COLORS[difficulty] ?? DIFFICULTY_COLORS[3];
}

export function getExampleLevel(level: number) {
  return EXAMPLE_LEVEL[level] ?? EXAMPLE_LEVEL[1];
}

export function categoryBadgeClasses(category: string): string {
  const c = getCategoryColor(category);
  return `${c.bg} ${c.text} border ${c.border}`;
}
