import type { ReactNode } from "react";

type Tone = "green" | "amber" | "red" | "blue" | "neutral";

const tones: Record<Tone, string> = {
  green: "border-gov-100 bg-gov-50 text-gov-900",
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  red: "border-red-200 bg-red-50 text-red-700",
  blue: "border-blue-200 bg-blue-50 text-blue-700",
  neutral: "border-border bg-surface text-muted"
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}
