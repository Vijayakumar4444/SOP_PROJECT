import type { ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Skeleton } from "./Skeleton";

interface AnalyticsPanelProps {
  title: string;
  description?: string;
  action?: ReactNode;
  loading?: boolean;
  error?: string | null;
  children: ReactNode;
  className?: string;
}

export function AnalyticsPanel({ title, description, action, loading, error, children, className = "" }: AnalyticsPanelProps) {
  return (
    <section className={`panel overflow-hidden ${className}`}>
      <div className="flex items-start justify-between gap-4 border-b-2 border-ink px-5 py-4">
        <div>
          <h2 className="text-base font-bold uppercase tracking-wide text-ink">{title}</h2>
          {description ? <p className="mt-1 text-sm leading-6 text-muted">{description}</p> : null}
        </div>
        {action}
      </div>
      <div className="p-5">
        {loading ? <Skeleton className="h-72" /> : null}
        {!loading && error ? (
          <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <span>{error}</span>
          </div>
        ) : null}
        {!loading && !error ? children : null}
      </div>
    </section>
  );
}
