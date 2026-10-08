import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { Database } from "lucide-react";
import { getSimulationResult } from "../../api/simulations.api";
import { AnalyticsPanel } from "../../components/ui/AnalyticsPanel";
import { Button } from "../../components/ui/Button";
import type { PolicyMemoryContext, PolicyMemoryMetricRange, SimilarPolicyMemory } from "../../types";
import { formatCompactNumber, formatCurrency, formatPercent } from "../../utils/format";

export default function SimulationResults() {
  const { simulationId = "SIM-TN-2026-1042" } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({ queryKey: ["simulation-result", simulationId], queryFn: () => getSimulationResult(simulationId) });
  const resultError = error as (Error & { status?: number; detail?: unknown }) | null;
  const resultNotReady = resultError?.status === 409;
  const prediction = data?.prediction;
  const backendOutput = data?.backendOutput;

  useEffect(() => {
    if (!resultNotReady) return undefined;
    const timer = window.setTimeout(() => navigate(`/loading/${simulationId}`), 1200);
    return () => window.clearTimeout(timer);
  }, [navigate, resultNotReady, simulationId]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 border-b-2 border-ink pb-6 xl:flex-row xl:items-start">
        <div>
          <div className="mb-3 inline-flex border-2 border-ink bg-gov-50 px-3 py-1 font-mono text-xs font-bold">STRICT BACKEND RESULT</div>
          <h1 className="text-4xl font-bold uppercase text-ink">{data?.simulation.policyName ?? "Simulation Results"}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="mono-value">{simulationId}</span>
          </div>
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
        ) : data && !prediction ? (
          <div className="border-2 border-ink bg-amber-50 p-5">
            <div className="text-sm font-bold uppercase tracking-wide text-muted">Strict prediction unavailable</div>
            <div className="mt-2 text-lg font-bold text-ink">This result was generated before the backend prediction contract existed.</div>
            <div className="mt-2 text-sm font-semibold text-muted">Rerun the full 8-phase backend pipeline to produce sample, statewide, benefit, and benchmark fields.</div>
          </div>
        ) : data && prediction ? (
          <div>
            <div className={`mb-5 border-2 border-ink px-5 py-6 ${outcomeClass(data.interpretation.classification)}`}>
              <div className="text-sm font-bold uppercase tracking-wide text-black">Policy Outcome</div>
              <div className="mt-2 text-5xl font-bold uppercase text-black">{data.interpretation.classification}</div>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <Summary label="Statewide Beneficiaries" value={formatCompactNumber(prediction.statewideEstimate.beneficiaries)} note="After implementation adjustment" />
              <Summary label="Sample Beneficiaries" value={formatCompactNumber(prediction.sample.beneficiaries)} note={`${formatCompactNumber(prediction.sample.population)} tested records`} />
              <Summary
                label="Submitted Benefit"
                value={formatCurrency(prediction.submittedPolicyBenefit.displayAmount ?? prediction.submittedPolicyBenefit.monthlyEquivalent)}
                note={prediction.submittedPolicyBenefit.displayLabel ?? "Submitted benefit parsed from policy"}
              />
              <Summary label="Prediction Error" value={prediction.actualPredictionError ? formatPercent(prediction.actualPredictionError.percentError) : "No benchmark"} note={prediction.officialBenchmark?.scheme} />
              <Summary label="Validation Status" value={prediction.validationStatus?.status ?? "Unbenchmarked"} note={prediction.validationStatus?.message} />
            </div>
          </div>
        ) : null}
      </AnalyticsPanel>

      {data && prediction ? (
        <>
          <section className="grid gap-4 xl:grid-cols-2">
            <AnalyticsPanel title="Sample vs Statewide Estimate">
              <div className="grid gap-3 sm:grid-cols-2">
                <Summary label="Sample Population" value={formatCompactNumber(prediction.sample.population)} />
                <Summary label="Sample Eligible" value={formatCompactNumber(prediction.sample.eligible)} />
                <Summary label="Sample Beneficiaries" value={formatCompactNumber(prediction.sample.beneficiaries)} />
                <Summary label="Sample Beneficiary Rate" value={formatPercent(prediction.sample.beneficiaryRate)} />
                <Summary label="Statewide Base Population" value={formatCompactNumber(prediction.statewideEstimate.basePopulation)} />
                <Summary label="Scale Factor" value={prediction.statewideEstimate.scaleFactor.toFixed(2)} />
                <Summary label="Statewide Eligible" value={formatCompactNumber(prediction.statewideEstimate.eligible)} />
                <Summary label="Raw Statewide Beneficiaries" value={formatCompactNumber(prediction.statewideEstimate.rawBeneficiariesBeforeImplementationAdjustment ?? prediction.statewideEstimate.beneficiaries)} />
                <Summary label="After Implementation Adj." value={formatCompactNumber(prediction.statewideEstimate.beneficiariesAfterImplementationAdjustment ?? prediction.statewideEstimate.beneficiaries)} />
                <Summary label="Statewide Beneficiaries" value={formatCompactNumber(prediction.statewideEstimate.beneficiaries)} />
              </div>
            </AnalyticsPanel>

            <AnalyticsPanel title="Benefit Amount Check">
              <div className="grid gap-3 sm:grid-cols-2">
                <Summary label={prediction.submittedPolicyBenefit.displayLabel ?? "Submitted Benefit"} value={formatCurrency(prediction.submittedPolicyBenefit.displayAmount ?? prediction.submittedPolicyBenefit.monthlyEquivalent)} />
                <Summary label="Submitted Annual Benefit" value={formatCurrency(prediction.submittedPolicyBenefit.annualAmount)} />
                <Summary label={prediction.pipelineArtifactBenefit.displayLabel ?? "Pipeline Annual Benefit"} value={formatCurrency(prediction.pipelineArtifactBenefit.displayAmount ?? prediction.pipelineArtifactBenefit.annualAmount)} />
                <Summary label="Pipeline Annual Benefit" value={formatCurrency(prediction.pipelineArtifactBenefit.annualAmount)} />
                <Summary label="Planned Statewide Budget" value={prediction.statewideEstimate.plannedStatewideBudget ? formatCurrency(prediction.statewideEstimate.plannedStatewideBudget) : "Not submitted"} />
                <Summary label="Statewide Cost, Submitted Benefit" value={formatCurrency(prediction.statewideEstimate.annualCostUsingSubmittedBenefit)} />
                <Summary label="Statewide Fiscal Pressure" value={typeof prediction.statewideEstimate.fiscalPressureUsingSubmittedBenefit === "number" ? formatPercent(prediction.statewideEstimate.fiscalPressureUsingSubmittedBenefit) : "No budget"} />
                <Summary label="Statewide Budget Surplus" value={typeof prediction.statewideEstimate.budgetSurplusUsingSubmittedBenefit === "number" ? formatCurrency(prediction.statewideEstimate.budgetSurplusUsingSubmittedBenefit) : "No budget"} />
              </div>
            </AnalyticsPanel>
          </section>

          {prediction.implementationAdjustment ? (
            <AnalyticsPanel title="Implementation Adjustment" description={prediction.implementationAdjustment.method}>
              <div className="grid gap-4 xl:grid-cols-[220px_1fr]">
                <Summary label="Adjustment Factor" value={formatPercent(prediction.implementationAdjustment.factor)} />
                <Summary label="Rule-Based Factor" value={typeof prediction.implementationAdjustment.ruleBasedFactor === "number" ? formatPercent(prediction.implementationAdjustment.ruleBasedFactor) : "N/A"} />
                <Summary label="Memory Prior Factor" value={typeof prediction.implementationAdjustment.memoryPriorFactor === "number" ? formatPercent(prediction.implementationAdjustment.memoryPriorFactor) : "No prior"} />
                <TextList title="Adjustment Reasons" items={prediction.implementationAdjustment.reasons} />
              </div>
            </AnalyticsPanel>
          ) : null}

          {prediction.benchmarkDeliveryCalibration?.applied ? (
            <AnalyticsPanel title="Benchmark Delivery Calibration" description={prediction.benchmarkDeliveryCalibration.method}>
              <div className="grid gap-4 xl:grid-cols-[220px_1fr]">
                <Summary label="Observed Delivery Factor" value={formatPercent(prediction.benchmarkDeliveryCalibration.observedDeliveryFactor ?? prediction.benchmarkDeliveryCalibration.factor)} />
                <Summary label="Applied Factor" value={formatPercent(prediction.benchmarkDeliveryCalibration.factor)} />
                {prediction.uncalibratedPredictionError ? (
                  <Summary label="Pre-Calibration Error" value={formatPercent(prediction.uncalibratedPredictionError.percentError)} />
                ) : null}
                <TextList title="Calibration Reasons" items={prediction.benchmarkDeliveryCalibration.reasons} />
              </div>
            </AnalyticsPanel>
          ) : null}

          {prediction.targetPopulationModel ? (
            <AnalyticsPanel title="Target Population Model" description={prediction.targetPopulationModel.method}>
              <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Summary label="Estimated Target Share" value={formatPercent(prediction.targetPopulationModel.estimatedTargetShare)} />
                  <Summary label="Estimated Target Population" value={formatCompactNumber(prediction.targetPopulationModel.estimatedTargetPopulation)} />
                  <Summary label="Target Cap Applied" value={prediction.targetPopulationModel.capApplied ? "Yes" : "No"} />
                </div>
                <TextList title="Target Constraints" items={prediction.targetPopulationModel.constraints} />
              </div>
            </AnalyticsPanel>
          ) : null}

          {prediction.officialBenchmark && prediction.actualPredictionError ? (
            <AnalyticsPanel title="Official Benchmark Comparison" description={prediction.officialBenchmark.source}>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Summary label="Official Actual Beneficiaries" value={formatCompactNumber(prediction.officialBenchmark.beneficiaries)} note={prediction.officialBenchmark.asOf} />
                <Summary label="Predicted Beneficiaries" value={formatCompactNumber(prediction.actualPredictionError.predictedBeneficiaries)} />
                <Summary label="Absolute Error" value={formatCompactNumber(prediction.actualPredictionError.absoluteError)} />
                <Summary label="Percent Error" value={formatPercent(prediction.actualPredictionError.percentError)} />
              </div>
            </AnalyticsPanel>
          ) : null}

          <AnalyticsPanel title="Backend Recommendation">
            <div className="space-y-4">
              <div className="border-2 border-ink bg-gov-50 p-4">
                <div className="text-xs font-bold uppercase tracking-wide text-muted">Summary</div>
                <div className="mt-2 text-sm font-semibold leading-6 text-ink">{data.interpretation.summary}</div>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <TextList title="Strengths" items={data.interpretation.strengths} />
                <TextList title="Concerns" items={data.interpretation.concerns} />
              </div>
            </div>
          </AnalyticsPanel>

          <AnalyticsPanel title="Backend Metadata">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Summary label="Result Source" value={backendOutput?.source ?? "N/A"} />
              <Summary label="Artifact Source" value={backendOutput?.artifactSource ?? "N/A"} />
              <Summary label="Evaluated Policy" value={backendOutput?.evaluatedPolicy ?? "N/A"} />
              <Summary label="Decision Basis" value={backendOutput?.decisionBasis ?? "N/A"} />
              <Summary label="Validation Status" value={backendOutput?.validationStatus ?? "N/A"} />
              <Summary label="Data Version" value={backendOutput?.dataVersion ?? "N/A"} />
              <Summary label="Benchmark Calibration" value={backendOutput?.benchmarkCalibrationApplied ? "Applied" : "Not applied"} />
              <Summary label="Result ID" value={backendOutput?.recommendationId ?? "N/A"} />
            </div>
          </AnalyticsPanel>

          <SimilarPoliciesPanel memory={data.memory} />
        </>
      ) : null}
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="border-2 border-ink p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{title}</div>
      <div className="mt-3 space-y-2">
        {items.length ? items.map((item) => <div key={item} className="text-sm font-semibold leading-6 text-ink">{item}</div>) : <div className="text-sm font-semibold text-muted">No backend item returned.</div>}
      </div>
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
            <PriorSummary label="Implementation prior" value={formatPriorRange(priors.implementationAdjustmentFactor, "percent")} />
            <PriorSummary label="Delivery prior" value={formatPriorRange(priors.observedDeliveryFactor, "percent")} />
            <PriorSummary label="Error prior" value={formatPriorRange(priors.predictionAbsolutePercentError, "percent")} />
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
        <MiniMetric label="Impl. Factor" value={formatOptionalPercent(policy.metrics.implementationAdjustmentFactor)} />
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

function outcomeClass(classification: string): string {
  if (classification === "Failure") return "bg-red-500";
  if (classification === "Moderate") return "bg-amber-300";
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
