import { formatPercent } from "../../utils/format";

export function RiskGauge({ score, overrun }: { score: number; overrun: number }) {
  const rotation = -90 + Math.min(100, Math.max(0, score)) * 1.8;
  return (
    <div className="grid items-center gap-5 md:grid-cols-[220px_1fr]">
      <div className="relative mx-auto h-32 w-56 overflow-hidden">
        <div className="absolute inset-x-0 top-4 h-48 rounded-t-full border-[22px] border-b-0 border-gov-100" />
        <div className="absolute inset-x-0 top-4 h-48 rounded-t-full border-[22px] border-b-0 border-gov-700" style={{ clipPath: `inset(0 ${100 - score}% 0 0)` }} />
        <div className="absolute bottom-0 left-1/2 h-1 w-24 origin-left rounded-full bg-ink transition-transform" style={{ transform: `rotate(${rotation}deg)` }} />
        <div className="absolute bottom-0 left-1/2 h-4 w-4 -translate-x-1/2 rounded-full bg-ink" />
      </div>
      <div className="space-y-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted">Risk Score</div>
          <div className="mono-value mt-1 text-3xl font-semibold text-ink">{score} / 100</div>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted">Probability of Exceeding Envelope</div>
          <div className="mono-value mt-1 text-xl font-semibold text-gov-900">{formatPercent(overrun)}</div>
        </div>
        <div className="grid grid-cols-4 gap-1 text-[11px] font-medium text-muted">
          <span>Low</span>
          <span>Moderate</span>
          <span>High</span>
          <span>Critical</span>
        </div>
      </div>
    </div>
  );
}
