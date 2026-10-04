import { useMemo, useState } from "react";
import type { DistrictResult } from "../../types";
import { formatCompactNumber, formatCurrency, formatPercent } from "../../utils/format";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

const metricLabels = {
  coverage: "Beneficiary %",
  beneficiaries: "Beneficiary Count",
  estimatedCost: "Estimated Cost",
  costPerBeneficiary: "Cost per Beneficiary",
  equityScore: "Equity Score",
  budgetPressure: "Fiscal Pressure",
  ruralCoverage: "Rural Coverage",
  urbanCoverage: "Urban Coverage"
} as const;

type Metric = keyof typeof metricLabels;

function metricValue(district: DistrictResult, metric: Metric): number {
  return district[metric];
}

function colorFor(value: number, min: number, max: number): string {
  const ratio = max === min ? 0.5 : (value - min) / (max - min);
  const shades = ["#DCFCE7", "#BBF7D0", "#86EFAC", "#4ADE80", "#16A34A", "#14532D"];
  return shades[Math.min(shades.length - 1, Math.max(0, Math.floor(ratio * shades.length)))];
}

export function TamilNaduMap({
  districts,
  selectedDistrict,
  onSelectDistrict
}: {
  districts: DistrictResult[];
  selectedDistrict?: DistrictResult;
  onSelectDistrict: (district: DistrictResult) => void;
}) {
  const [metric, setMetric] = useState<Metric>("coverage");
  const extent = useMemo(() => {
    const values = districts.map((district) => metricValue(district, metric));
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [districts, metric]);

  return (
    <div className="grid gap-5 xl:grid-cols-[1.2fr_360px]">
      <div>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {(Object.keys(metricLabels) as Metric[]).map((item) => (
            <button
              key={item}
              type="button"
              className={`focus-ring rounded-full border px-3 py-1.5 text-xs font-medium ${
                metric === item ? "border-gov-700 bg-gov-50 text-gov-900" : "border-border text-muted hover:bg-surface"
              }`}
              onClick={() => setMetric(item)}
            >
              {metricLabels[item]}
            </button>
          ))}
        </div>
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-5 lg:grid-cols-6">
            {districts.map((district) => (
              <button
                key={district.id}
                type="button"
                className={`focus-ring min-h-[76px] rounded-md border p-2 text-left transition hover:-translate-y-0.5 ${
                  selectedDistrict?.id === district.id ? "border-gov-900 ring-2 ring-gov-100" : "border-white"
                }`}
                style={{ backgroundColor: colorFor(metricValue(district, metric), extent.min, extent.max) }}
                onClick={() => onSelectDistrict(district)}
                title={`${district.district}: ${formatPercent(district.coverage)}`}
              >
                <div className="text-xs font-semibold text-ink">{district.district}</div>
                <div className="mono-value mt-2 text-sm font-semibold text-gov-900">
                  {metric.includes("Coverage") || metric === "coverage" || metric === "budgetPressure"
                    ? formatPercent(metricValue(district, metric))
                    : metric === "estimatedCost" || metric === "costPerBeneficiary"
                      ? formatCurrency(metricValue(district, metric))
                      : formatCompactNumber(metricValue(district, metric))}
                </div>
              </button>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-muted">
            District choropleth uses the same service contract as the production GeoJSON layer. When official boundaries are available, this component can switch to MapLibre or Leaflet without changing result screens.
          </p>
        </div>
      </div>
      <DistrictDrawer district={selectedDistrict ?? districts[0]} />
    </div>
  );
}

function DistrictDrawer({ district }: { district: DistrictResult }) {
  return (
    <aside className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">{district.district} District</h3>
          <p className="mt-1 text-sm text-muted">District drill-down summary</p>
        </div>
        <Badge tone={district.equityScore >= 85 ? "green" : district.equityScore >= 75 ? "amber" : "red"}>
          Equity {district.equityScore}
        </Badge>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3">
        {[
          ["Population", formatCompactNumber(district.population)],
          ["Eligible", formatCompactNumber(district.eligiblePopulation)],
          ["Beneficiaries", formatCompactNumber(district.beneficiaries)],
          ["Coverage", formatPercent(district.coverage)],
          ["Est. cost", formatCurrency(district.estimatedCost)],
          ["Cost / beneficiary", formatCurrency(district.costPerBeneficiary)]
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-border bg-surface p-3">
            <div className="text-xs text-muted">{label}</div>
            <div className="mono-value mt-1 text-sm font-semibold text-ink">{value}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 space-y-3">
        <MiniBar label="Rural coverage" value={district.ruralCoverage} />
        <MiniBar label="Urban coverage" value={district.urbanCoverage} />
        <MiniBar label="Fiscal pressure" value={district.budgetPressure} />
      </div>
      <Button className="mt-5 w-full" variant="secondary">
        Compare District
      </Button>
    </aside>
  );
}

function MiniBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="font-medium text-muted">{label}</span>
        <span className="mono-value text-ink">{formatPercent(value)}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-gov-100">
        <div className="h-2 rounded-full bg-gov-700" style={{ width: `${Math.min(100, value * 100)}%` }} />
      </div>
    </div>
  );
}
