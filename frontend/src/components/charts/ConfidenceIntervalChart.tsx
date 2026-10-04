import type { ConfidenceInterval } from "../../types";
import { formatMetric } from "../../utils/format";

export function ConfidenceIntervalChart({ intervals }: { intervals: ConfidenceInterval[] }) {
  return (
    <div className="space-y-5">
      {intervals.map((interval) => {
        const range = interval.upper - interval.lower;
        const estimatePct = range === 0 ? 50 : ((interval.estimate - interval.lower) / range) * 100;
        return (
          <div key={interval.metric}>
            <div className="flex items-center justify-between gap-4">
              <div className="text-sm font-semibold text-ink">{interval.metric}</div>
              <div className="mono-value text-sm text-gov-900">{formatMetric(interval.estimate, interval.formatter)}</div>
            </div>
            <div className="mt-3 grid grid-cols-[auto_1fr_auto] items-center gap-3 text-xs text-muted">
              <span className="mono-value">{formatMetric(interval.lower, interval.formatter)}</span>
              <div className="relative h-2 rounded-full bg-gov-100">
                <div className="absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-white bg-gov-700 shadow-soft" style={{ left: `${estimatePct}%` }} />
              </div>
              <span className="mono-value">{formatMetric(interval.upper, interval.formatter)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
