import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { Database, Download, SlidersHorizontal } from "lucide-react";
import { motion } from "framer-motion";
import type { EChartsOption } from "echarts";
import { getSimulationResult } from "../../api/simulations.api";
import { AnalyticsPanel } from "../../components/ui/AnalyticsPanel";
import { Button } from "../../components/ui/Button";
import { EChartsPanel } from "../../components/charts/EChartsPanel";
import { ConfidenceIntervalChart } from "../../components/charts/ConfidenceIntervalChart";
import { RiskGauge } from "../../components/charts/RiskGauge";
import { TamilNaduMap } from "../../components/maps/TamilNaduMap";
import type { DistrictResult, PolicyMemoryContext, PolicyMemoryMetricRange, SimilarPolicyMemory } from "../../types";
import { formatCompactNumber, formatCurrency, formatPercent } from "../../utils/format";
import { exportSimulationPdf } from "../../utils/exportPdf";

export default function SimulationResults() {
  const { simulationId = "SIM-TN-2026-1042" } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({ queryKey: ["simulation-result", simulationId], queryFn: () => getSimulationResult(simulationId) });
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictResult | undefined>();
  const [districtMode, setDistrictMode] = useState<"percent" | "count">("percent");
  const [exportingPdf, setExportingPdf] = useState(false);
  const resultError = error as (Error & { status?: number; detail?: unknown }) | null;
  const resultNotReady = resultError?.status === 409;

  useEffect(() => {
    if (!resultNotReady) return undefined;
    const timer = window.setTimeout(() => navigate(`/loading/${simulationId}`), 1200);
    return () => window.clearTimeout(timer);
  }, [navigate, resultNotReady, simulationId]);

  function handleExportPdf() {
    if (!data) return;
    setExportingPdf(true);
    try {
      exportSimulationPdf(data);
    } finally {
      window.setTimeout(() => setExportingPdf(false), 250);
    }
  }

  const districtOption: EChartsOption | undefined = useMemo(() => {
    if (!data) return undefined;
    const sorted = [...data.districts].sort((a, b) => (districtMode === "percent" ? b.coverage - a.coverage : b.beneficiaries - a.beneficiaries));
    return {
      yAxis: { type: "category", data: sorted.map((district) => district.district), inverse: true },
      xAxis: { type: "value" },
      series: [
        {
          type: "bar",
          data: sorted.map((district) => (districtMode === "percent" ? Math.round(district.coverage * 1000) / 10 : district.beneficiaries)),
          barWidth: 14,
          markLine: districtMode === "percent" ? { data: [{ xAxis: Math.round(data.beneficiary.coverage * 1000) / 10, name: "Average" }] } : undefined
        }
      ]
    };
  }, [data, districtMode]);

  const demographicOptions = useMemo<Record<string, EChartsOption>>(() => {
    if (!data) return {} as Record<string, EChartsOption>;
    return {
      gender: {
        tooltip: { trigger: "item" },
        series: [{ type: "pie", radius: ["52%", "76%"], data: data.demographics.gender.map((item) => ({ name: item.category, value: item.value })) }]
      },
      age: {
        xAxis: { type: "category", data: data.demographics.ageGroup.map((item) => item.category) },
        yAxis: { type: "value" },
        series: [{ type: "bar", data: data.demographics.ageGroup.map((item) => item.value), barWidth: 28 }]
      },
      ruralUrban: {
        legend: { bottom: 0 },
        xAxis: { type: "category", data: data.demographics.ruralUrban.map((item) => item.category) },
        yAxis: { type: "value" },
        series: [
          { name: "Beneficiaries", type: "bar", stack: "total", data: data.demographics.ruralUrban.map((item) => item.beneficiaries) },
          { name: "Non-beneficiaries", type: "bar", stack: "total", data: data.demographics.ruralUrban.map((item) => item.nonBeneficiaries) }
        ]
      }
    } satisfies Record<string, EChartsOption>;
  }, [data]);

  const monteCarloOption: EChartsOption | undefined = data
    ? {
        xAxis: { type: "category", data: data.monteCarlo.buckets.map((bucket) => `${formatCurrency(bucket.lower)}-${formatCurrency(bucket.upper)}`), axisLabel: { rotate: 35 } },
        yAxis: { type: "value" },
        series: [{ type: "bar", data: data.monteCarlo.buckets.map((bucket) => bucket.frequency), barWidth: 18 }],
        markLine: { data: [{ xAxis: data.monteCarlo.buckets.length - 1, name: "Envelope" }] }
      }
    : undefined;

  const performanceOption: EChartsOption | undefined = data
    ? {
        radar: {
          indicator: [
            { name: "Coverage", max: 100 },
            { name: "Target Fit", max: 100 },
            { name: "Equity", max: 100 },
            { name: "Fiscal", max: 100 },
            { name: "Benefit", max: 100 },
            { name: "Risk Control", max: 100 }
          ]
        },
        series: [
          {
            type: "radar",
            areaStyle: { opacity: 0.18 },
            data: [
              {
                name: "Policy Performance",
                value: [
                  data.beneficiary.coverage * 100,
                  data.beneficiary.targetFit,
                  data.equity.overall,
                  data.budget.utilization * 100,
                  82,
                  100 - data.budget.riskScore
                ]
              }
            ]
          }
        ]
      }
    : undefined;

  const riskBenefitOption: EChartsOption | undefined = data
    ? {
        xAxis: { type: "value", name: "Cost" },
        yAxis: { type: "value", name: "Coverage" },
        series: [
          {
            type: "scatter",
            symbolSize: 18,
            data: data.districts.map((district) => [district.estimatedCost / 1_000_000, district.coverage * 100, district.district])
          }
        ]
      }
    : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 border-b-2 border-ink pb-6 xl:flex-row xl:items-start">
        <div>
          <div className="mb-3 inline-flex border-2 border-ink bg-gov-50 px-3 py-1 font-mono text-xs font-bold">RESULT PAGE</div>
          <h1 className="text-4xl font-bold uppercase text-ink">{data?.simulation.policyName ?? "Simulation Results"}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="mono-value">{simulationId}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button icon={<Download className="h-4 w-4" />} onClick={handleExportPdf} disabled={!data || exportingPdf}>
            {exportingPdf ? "Preparing PDF" : "Export PDF"}
          </Button>
        </div>
      </div>

      <AnalyticsPanel title="Policy Outcome" loading={isLoading} error={!resultNotReady && error instanceof Error ? error.message : null}>
        {resultNotReady ? (
          <div className="border-2 border-ink bg-gov-50 p-5">
            <div className="text-sm font-bold uppercase tracking-wide text-muted">Backend pipeline still running</div>
            <div className="mt-2 text-lg font-bold text-ink">Final results are shown only after all 8 backend phases finish.</div>
            <div className="mt-2 text-sm font-semibold text-muted">Returning to the live progress page for this simulation.</div>
            <Button className="mt-4" onClick={() => navigate(`/loading/${simulationId}`)}>
              View Live Progress
            </Button>
          </div>
        ) : data ? (
          <div>
            <motion.div
              className={`mb-5 border-2 border-ink px-5 py-6 ${outcomeClass(data.interpretation.classification)}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <div className="text-sm font-bold uppercase tracking-wide text-black">Policy Outcome</div>
              <div className="mt-2 text-5xl font-bold uppercase text-black">{outcomeLabel(data.interpretation.classification)}</div>
            </motion.div>
            <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
            <Summary label="Beneficiary Coverage" value={formatPercent(data.beneficiary.coverage)} note={data.beneficiary.targetUniverse} />
            <Summary label="Target Fit" value={`${data.beneficiary.targetFit} / 100`} note="Real-world alignment" />
            <Summary label="Target Population" value={formatCompactNumber(data.beneficiary.targetPopulation)} note="Tested group" />
            <Summary label="Total Beneficiaries" value={formatCompactNumber(data.beneficiary.beneficiaries)} />
            <Summary label="Estimated Cost" value={formatCurrency(data.budget.meanCost)} note="Mean scenario" />
            <Summary label="Fiscal Pressure" value={formatPercent(data.budget.utilization)} note="Backend estimate" />
            <Summary label="Equity Score" value={`${data.equity.overall} / 100`} note="Composite score" />
            <Summary label="Risk Score" value={`${data.budget.riskScore} / 100`} note={data.budget.riskLevel} />
            </div>
          </div>
        ) : null}
      </AnalyticsPanel>

      {data ? (
        <>
          <SimilarPoliciesPanel memory={data.memory} />

          <section className="grid gap-4">
            <AnalyticsPanel title="Beneficiary Coverage">
              <div className="grid gap-5 xl:grid-cols-[260px_1fr]">
                <div className="rounded-md border-2 border-ink bg-gov-50 p-5">
                  <div className="text-xs font-bold uppercase tracking-wide text-muted">Coverage Against Target Group</div>
                  <div className="mono-value mt-3 text-5xl font-semibold text-gov-900">{formatPercent(data.beneficiary.coverage)}</div>
                  <div className="mt-4 h-4 rounded-full bg-white">
                    <div className="h-4 rounded-full bg-gov-700" style={{ width: `${Math.min(100, data.beneficiary.coverage * 100)}%` }} />
                  </div>
                  <div className="mt-3 text-sm font-semibold leading-5 text-ink">{data.beneficiary.targetUniverse}</div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  <Summary label="Base population" value={formatCompactNumber(data.beneficiary.basePopulation)} note="Synthetic population" />
                  <Summary label="Target group tested" value={data.beneficiary.targetUniverse} note={`${formatPercent(data.beneficiary.targetShare)} of base`} />
                  <Summary label="Target population" value={formatCompactNumber(data.beneficiary.targetPopulation)} note="Coverage denominator" />
                  <Summary label="Beneficiaries" value={formatCompactNumber(data.beneficiary.beneficiaries)} />
                  <Summary label="Not reached in target" value={formatCompactNumber(data.beneficiary.nonEligiblePopulation)} />
                </div>
              </div>
            </AnalyticsPanel>
            <AnalyticsPanel title="Fiscal Analysis">
              <div className="grid gap-3 sm:grid-cols-2">
                <Summary label="Planning Envelope" value={formatCurrency(data.budget.allocatedBudget)} />
                <Summary label="Estimated Mean Cost" value={formatCurrency(data.budget.meanCost)} />
                <Summary label="Cost per Beneficiary" value={formatCurrency(data.budget.costPerBeneficiary)} />
                <Summary label="Worst Case Cost" value={formatCurrency(data.budget.worstCaseCost)} />
              </div>
            </AnalyticsPanel>
          </section>

          <AnalyticsPanel
            title="District-Wise Beneficiary Chart"
            action={<Button icon={<SlidersHorizontal className="h-4 w-4" />} onClick={() => setDistrictMode(districtMode === "percent" ? "count" : "percent")}>{districtMode === "percent" ? "Percentage" : "Count"}</Button>}
          >
            {districtOption ? <EChartsPanel option={districtOption} height={520} ariaLabel="District-wise beneficiary coverage chart" /> : null}
          </AnalyticsPanel>

          <AnalyticsPanel title="Tamil Nadu District Map" description="Choropleth district analysis with drill-down metrics.">
            <TamilNaduMap districts={data.districts} selectedDistrict={selectedDistrict} onSelectDistrict={setSelectedDistrict} />
          </AnalyticsPanel>

          <section className="grid gap-4 xl:grid-cols-3">
            <AnalyticsPanel title="Gender Breakdown">
              {"gender" in demographicOptions ? <EChartsPanel option={demographicOptions.gender} height={260} ariaLabel="Gender beneficiary donut chart" /> : null}
            </AnalyticsPanel>
            <AnalyticsPanel title="Age Group">
              {"age" in demographicOptions ? <EChartsPanel option={demographicOptions.age} height={260} ariaLabel="Age group beneficiary histogram" /> : null}
            </AnalyticsPanel>
            <AnalyticsPanel title="Rural / Urban">
              {"ruralUrban" in demographicOptions ? <EChartsPanel option={demographicOptions.ruralUrban} height={260} ariaLabel="Rural urban stacked beneficiary chart" /> : null}
            </AnalyticsPanel>
          </section>

          <AnalyticsPanel title="Monte Carlo Expenditure Distribution">
            {monteCarloOption ? <EChartsPanel option={monteCarloOption} height={360} ariaLabel="Monte Carlo expenditure distribution histogram" /> : null}
            <div className="mt-4 grid gap-3 sm:grid-cols-5">
              <Summary label="Mean Cost" value={formatCurrency(data.monteCarlo.mean)} />
              <Summary label="Median" value={formatCurrency(data.monteCarlo.median)} />
              <Summary label="95% CI" value={`${formatCurrency(data.monteCarlo.p5)} - ${formatCurrency(data.monteCarlo.p95)}`} />
              <Summary label="Planning Envelope" value={formatCurrency(data.monteCarlo.budget)} />
              <Summary label="P(Cost > Envelope)" value={formatPercent(data.monteCarlo.overrunProbability)} />
            </div>
          </AnalyticsPanel>

          <section className="grid gap-4 xl:grid-cols-2">
            <AnalyticsPanel title="Policy Performance">
              {performanceOption ? <EChartsPanel option={performanceOption} height={360} ariaLabel="Radar chart of policy performance" /> : null}
            </AnalyticsPanel>
            <AnalyticsPanel title="Risk vs Benefit">
              {riskBenefitOption ? <EChartsPanel option={riskBenefitOption} height={360} ariaLabel="Scatter chart of district cost and coverage" /> : null}
            </AnalyticsPanel>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <AnalyticsPanel title="Confidence Intervals">
              <ConfidenceIntervalChart intervals={data.confidenceIntervals} />
            </AnalyticsPanel>
            <AnalyticsPanel title="Fiscal Risk">
              <RiskGauge score={data.budget.riskScore} overrun={data.budget.probabilityOverrun} />
            </AnalyticsPanel>
          </section>

          <AnalyticsPanel title="Fairness / Equity Score" description={data.equity.explanation}>
            <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
              <div className="rounded-lg border border-border bg-surface p-5 text-center">
                <div className="text-xs uppercase tracking-wide text-muted">Overall Equity</div>
                <div className="mono-value mt-3 text-5xl font-semibold text-gov-900">{data.equity.overall}</div>
                <div className="mt-1 text-sm text-muted">/ 100</div>
              </div>
              <div className="space-y-3">
                {[
                  ["Gender Equity", data.equity.gender],
                  ["Social Group", data.equity.socialGroup],
                  ["Rural-Urban", data.equity.ruralUrban],
                  ["District Equity", data.equity.district],
                  ["Income Equity", data.equity.income]
                ].map(([label, value]) => (
                  <div key={label as string}>
                    <div className="flex justify-between text-sm"><span className="font-medium text-ink">{label}</span><span className="mono-value">{value}</span></div>
                    <div className="mt-1 h-2 rounded-full bg-gov-100"><div className="h-2 rounded-full bg-gov-700" style={{ width: `${value}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>
          </AnalyticsPanel>

          <AnalyticsPanel title="Policy Improvements">
            <div className="grid gap-3 lg:grid-cols-3">
              {[
                ["Income eligibility threshold", "Adjust threshold by district cost pressure", "Higher coverage efficiency"],
                ["Low-performing districts", "Target outreach in bottom 5 districts", "Improved district equity"],
                ["Benefit amount", "Optimize transfer value against p95 cost", "Lower budget risk"],
                ["Rural inclusion", "Increase rural implementation weight", "Stronger rural coverage"],
                ["Social group equity", "Review under-served group access", "Improved inclusion score"],
                ["Fiscal pressure", "Add fiscal guardrail trigger", "Reduced overrun probability"]
              ].map(([current, suggested, impact]) => (
                <div key={current} className="border-2 border-ink p-4">
                  <div className="text-xs font-bold uppercase text-muted">Current Policy</div>
                  <div className="mt-1 font-bold text-ink">{current}</div>
                  <div className="mt-4 text-xs font-bold uppercase text-muted">Suggested Change</div>
                  <div className="mt-1 text-sm font-semibold text-ink">{suggested}</div>
                  <div className="mt-4 bg-gov-50 p-2 font-mono text-xs font-bold text-gov-900">{impact}</div>
                </div>
              ))}
            </div>
          </AnalyticsPanel>
        </>
      ) : null}
    </div>
  );
}

function SimilarPoliciesPanel({ memory }: { memory?: PolicyMemoryContext }) {
  const similarPolicies = memory?.similarPolicies ?? [];
  if (!similarPolicies.length) return null;
  const priors = memory?.priors ?? {};
  return (
    <AnalyticsPanel
      title="Similar Policies Used"
      description="Historical completed pipeline results used as calibration memory for this simulation."
      action={
        <div className="inline-flex items-center gap-2 border-2 border-ink bg-gov-50 px-3 py-2 text-xs font-bold uppercase text-ink">
          <Database className="h-4 w-4" />
          {memory?.similarPolicyCount ?? similarPolicies.length} Match{(memory?.similarPolicyCount ?? similarPolicies.length) === 1 ? "" : "es"}
        </div>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
        <div className="grid gap-3 lg:grid-cols-2">
          {similarPolicies.slice(0, 4).map((policy) => (
            <SimilarPolicyCard key={policy.runId} policy={policy} />
          ))}
        </div>
        <div className="border-2 border-ink bg-white p-4">
          <div className="text-xs font-bold uppercase tracking-wide text-muted">DB Prior Summary</div>
          <div className="mt-3 grid gap-3">
            <PriorSummary label="Coverage prior" value={formatPriorRange(priors.coverage, "percent")} />
            <PriorSummary label="Risk prior" value={formatPriorRange(priors.riskScore, "score")} />
            <PriorSummary label="Equity prior" value={formatPriorRange(priors.equityScore, "score")} />
            <PriorSummary label="Benefit prior" value={formatPriorRange(priors.benefitAmount, "currency")} />
          </div>
          {priors.outcomes ? (
            <div className="mt-4">
              <div className="text-xs font-bold uppercase tracking-wide text-muted">Past Outcomes</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(priors.outcomes).map(([outcome, count]) => (
                  <span key={outcome} className="border-2 border-ink bg-gov-50 px-2 py-1 text-xs font-bold text-ink">
                    {outcome}: {count}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AnalyticsPanel>
  );
}

function SimilarPolicyCard({ policy }: { policy: SimilarPolicyMemory }) {
  return (
    <div className="min-w-0 border-2 border-ink bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="break-words text-base font-bold text-ink">{policy.policyName ?? policy.runId}</div>
          <div className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">{policy.department ?? "Previous simulation"}</div>
        </div>
        <div className="shrink-0 border-2 border-ink bg-gov-600 px-2 py-1 font-mono text-sm font-bold text-black">
          {Math.round(policy.similarityScore * 100)}%
        </div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <MiniMetric label="Coverage" value={formatOptionalPercent(policy.metrics.coverage)} />
        <MiniMetric label="Target Fit" value={formatOptionalScore(policy.metrics.targetFit)} />
        <MiniMetric label="Fiscal Pressure" value={formatOptionalPercent(policy.metrics.fiscalPressure)} />
        <MiniMetric label="Outcome" value={policy.metrics.finalOutcome ?? "N/A"} />
      </div>
      {policy.reasons.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {policy.reasons.map((reason) => (
            <span key={reason} className="border border-ink px-2 py-1 text-xs font-semibold text-ink">
              {reason}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 bg-gov-50 p-2">
      <div className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 break-words text-sm font-bold text-ink">{value}</div>
    </div>
  );
}

function PriorSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border bg-gov-50 p-3">
      <div className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 break-words text-sm font-bold text-ink">{value}</div>
    </div>
  );
}

function Summary({ label, value, note }: { label: string; value: string; note?: string }) {
  const longValue = value.length > 18;
  return (
    <div className="min-w-0 rounded-md border-2 border-ink bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className={`${longValue ? "text-base leading-6" : "mono-value text-xl"} mt-2 break-words font-semibold text-ink`}>{value}</div>
      {note ? <div className="mt-1 break-words text-xs font-semibold text-muted">{note}</div> : null}
    </div>
  );
}

function outcomeLabel(classification: string): string {
  return classification;
}

function outcomeClass(classification: string): string {
  const label = outcomeLabel(classification);
  if (label === "Failure") return "bg-red-500";
  if (label === "Moderate") return "bg-amber-300";
  return "bg-gov-600";
}

function formatOptionalPercent(value?: number | null): string {
  return typeof value === "number" ? formatPercent(value) : "N/A";
}

function formatOptionalScore(value?: number | null): string {
  return typeof value === "number" ? `${Math.round(value)} / 100` : "N/A";
}

function formatPriorRange(range: PolicyMemoryMetricRange | undefined, mode: "percent" | "score" | "currency"): string {
  if (!range || typeof range.mean !== "number") return "No prior";
  if (mode === "percent") return `${formatPercent(range.mean)} (${formatPercent(range.min ?? range.mean)}-${formatPercent(range.max ?? range.mean)})`;
  if (mode === "currency") return `${formatCurrency(range.mean)} (${formatCurrency(range.min ?? range.mean)}-${formatCurrency(range.max ?? range.mean)})`;
  return `${Math.round(range.mean)} (${Math.round(range.min ?? range.mean)}-${Math.round(range.max ?? range.mean)})`;
}

