import { useMemo, useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";
import { Database, Play, Plus, Trash2 } from "lucide-react";
import { createSimulation, startSimulationPipeline } from "../../api/simulations.api";
import { departments, ruleAttributes, tamilNaduDistricts } from "../../constants";
import { useAppStore } from "../../stores/useAppStore";
import type { BenefitFrequency, GeographicScope, Policy, PolicyRule, RuleOperator } from "../../types";
import { Button } from "../../components/ui/Button";

const operators: RuleOperator[] = ["=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "BETWEEN"];
const runPresets = [
  { label: "1K", value: 1_000 },
  { label: "5K", value: 5_000 },
  { label: "10K", value: 10_000 },
  { label: "25K", value: 25_000 },
  { label: "50K", value: 50_000 },
  { label: "100K", value: 100_000 }
];

export default function NewSimulation() {
  const navigate = useNavigate();
  const draft = useAppStore((state) => state.policyDraft);
  const configuration = useAppStore((state) => state.configuration);
  const setDraft = useAppStore((state) => state.setPolicyDraft);
  const setConfiguration = useAppStore((state) => state.setConfiguration);
  const [rules, setRules] = useState<PolicyRule[]>(draft.rules);
  const [customRuns, setCustomRuns] = useState("");
  const form = useForm<Policy>({ defaultValues: draft });
  const policy = { ...form.watch(), rules };

  const createMutation = useMutation({
    mutationFn: async (payload: { policy: Policy; configuration: typeof configuration }) => {
      const created = await createSimulation(payload);
      await startSimulationPipeline(created.simulationId);
      return created;
    },
    onSuccess: ({ simulationId }) => navigate(`/loading/${simulationId}`)
  });

  const rulePreview = useMemo(
    () => rules.map((rule, index) => `${index === 0 ? "" : `${rule.joiner} `}${rule.attribute} ${rule.operator} ${rule.value}`).join("\n"),
    [rules]
  );
  const watchedScope = form.watch("geographicScope");
  const watchedBenefitAmount = form.watch("benefitAmount");
  const watchedBenefitFrequency = form.watch("benefitFrequency");
  const watchedBudget = form.watch("budgetAllocation");
  const watchedBenchmark = form.watch("benchmarkActualBeneficiaries");

  function updateRule(id: string, next: Partial<PolicyRule>) {
    setRules((current) => current.map((rule) => (rule.id === id ? { ...rule, ...next } : rule)));
  }

  function addRule() {
    setRules((current) => [...current, { id: crypto.randomUUID(), attribute: "District", operator: "=", value: "Tamil Nadu", joiner: "AND" }]);
  }

  function runSimulation() {
    const cleanedPolicy = sanitizePolicy(policy);
    setDraft(cleanedPolicy);
    createMutation.mutate({ policy: cleanedPolicy, configuration });
  }

  return (
    <div className="mx-auto max-w-6xl">
      <section className="mb-8 grid gap-5 border-b-2 border-ink pb-6 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 border-2 border-ink px-3 py-1 font-mono text-xs font-bold">
            <Database className="h-4 w-4" />
            POLICY INPUT
          </div>
          <h1 className="text-4xl font-bold uppercase tracking-normal text-ink">Government Policy Simulation</h1>
        </div>
        <div className="border-2 border-ink bg-gov-50 px-4 py-3 text-right">
          <div className="text-xs font-bold uppercase text-muted">Monte Carlo Size</div>
          <div className="mono-value text-2xl font-bold text-ink">{configuration.monteCarloRuns.toLocaleString("en-IN")}</div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <main className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Policy Name">
              <input className="field" {...form.register("name")} />
            </Field>
            <Field label="Department">
              <select className="field" {...form.register("department")}>
                {departments.map((department) => (
                  <option key={department}>{department}</option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Policy Description">
            <textarea className="field min-h-32 resize-y leading-6" {...form.register("description")} />
          </Field>

          <Field label="Policy Objective">
            <textarea className="field min-h-20 resize-y leading-6" {...form.register("objectives")} />
          </Field>

          <div className="grid gap-4 md:grid-cols-3">
            <NumberField label="Benefit Amount" registration={form.register("benefitAmount", { valueAsNumber: true })} placeholder="1000" />
            <Field label="Benefit Frequency">
              <select className="field" {...form.register("benefitFrequency")}>
                {(["Monthly", "Annual", "One-time"] satisfies BenefitFrequency[]).map((frequency) => (
                  <option key={frequency}>{frequency}</option>
                ))}
              </select>
            </Field>
            <NumberField label="Admin Cost %" registration={form.register("administrativeCostPercent", { valueAsNumber: true })} placeholder="0" />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <NumberField label="Planned Statewide Budget" registration={form.register("budgetAllocation", { valueAsNumber: true })} placeholder="17238828000" />
            <Field label="Geographic Scope">
              <select className="field" {...form.register("geographicScope")}>
                {(["Tamil Nadu", "Selected Districts", "Rural Only", "Urban Only"] satisfies GeographicScope[]).map((scope) => (
                  <option key={scope}>{scope}</option>
                ))}
              </select>
            </Field>
          </div>

          {watchedScope === "Selected Districts" ? (
            <Field label="Selected Districts">
              <select
                className="field min-h-36"
                multiple
                value={form.watch("selectedDistricts")}
                onChange={(event) =>
                  form.setValue(
                    "selectedDistricts",
                    Array.from(event.target.selectedOptions, (option) => option.value),
                    { shouldDirty: true }
                  )
                }
              >
                {tamilNaduDistricts.map((district) => (
                  <option key={district}>{district}</option>
                ))}
              </select>
            </Field>
          ) : null}

          <Field label="Eligibility / Policy Rules">
            <div className="space-y-2">
              {rules.map((rule, index) => (
                <div key={rule.id} className="grid gap-2 md:grid-cols-[82px_1fr_110px_1fr_42px]">
                  <select className="field py-2" value={rule.joiner} disabled={index === 0} onChange={(event) => updateRule(rule.id, { joiner: event.target.value as PolicyRule["joiner"] })}>
                    <option>AND</option>
                    <option>OR</option>
                  </select>
                  <select className="field py-2" value={rule.attribute} onChange={(event) => updateRule(rule.id, { attribute: event.target.value })}>
                    {ruleAttributes.map((attribute) => (
                      <option key={attribute}>{attribute}</option>
                    ))}
                  </select>
                  <select className="field py-2 font-mono" value={rule.operator} onChange={(event) => updateRule(rule.id, { operator: event.target.value as RuleOperator })}>
                    {operators.map((operator) => (
                      <option key={operator}>{operator}</option>
                    ))}
                  </select>
                  <input className="field py-2" value={rule.value} onChange={(event) => updateRule(rule.id, { value: event.target.value })} />
                  <button className="focus-ring border-2 border-ink p-2 hover:bg-red-50" type="button" onClick={() => setRules((current) => current.filter((item) => item.id !== rule.id))} aria-label="Remove rule">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <Button icon={<Plus className="h-4 w-4" />} onClick={addRule}>
                Add Rule
              </Button>
            </div>
          </Field>

          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Monte Carlo Simulation Size">
              <div className="grid grid-cols-4 gap-2">
                {runPresets.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    className={`focus-ring border-2 border-ink px-3 py-2 font-mono text-sm font-bold ${configuration.monteCarloRuns === preset.value ? "bg-gov-600 text-black" : "bg-white"}`}
                    onClick={() => setConfiguration({ ...configuration, monteCarloRuns: preset.value })}
                  >
                    {preset.label}
                  </button>
                ))}
                <input
                  className="field col-span-4 font-mono"
                  placeholder="Custom"
                  value={customRuns}
                  onChange={(event) => {
                    setCustomRuns(event.target.value);
                    const value = Number(event.target.value);
                    if (value > 0) setConfiguration({ ...configuration, monteCarloRuns: value });
                  }}
                />
              </div>
            </Field>
            <Field label="Confidence Level">
              <select
                className="field font-mono"
                value={configuration.confidenceLevel}
                onChange={(event) => setConfiguration({ ...configuration, confidenceLevel: Number(event.target.value) as 90 | 95 | 99 })}
              >
                <option value={90}>90%</option>
                <option value={95}>95%</option>
                <option value={99}>99%</option>
              </select>
            </Field>
          </div>

          <section className="border-2 border-ink p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide">Advanced Simulation Settings</h2>
            <div className="grid gap-4 md:grid-cols-3">
              <NumberField
                label="Population Sample Size"
                value={configuration.populationSampleSize}
                min={1}
                onValueChange={(value) => setConfiguration({ ...configuration, populationSampleSize: value })}
              />
              <NumberField
                label="Random Seed"
                value={configuration.randomSeed ?? ""}
                min={0}
                onValueChange={(value) => setConfiguration({ ...configuration, randomSeed: value })}
              />
              <Field label="Pipeline Controls">
                <div className="grid gap-2">
                  <Toggle
                    label="Budget constraint"
                    checked={configuration.budgetConstraint}
                    onChange={(checked) => setConfiguration({ ...configuration, budgetConstraint: checked })}
                  />
                  <Toggle
                    label="Sensitivity analysis"
                    checked={configuration.sensitivityAnalysis}
                    onChange={(checked) => setConfiguration({ ...configuration, sensitivityAnalysis: checked })}
                  />
                </div>
              </Field>
            </div>
          </section>

          <section className="border-2 border-ink p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide">Official Benchmark</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <NumberField label="Actual Beneficiaries" registration={form.register("benchmarkActualBeneficiaries", { valueAsNumber: true })} placeholder="1436569" />
              <NumberField label="Official Actual Annual Cost" registration={form.register("benchmarkActualAnnualCost", { valueAsNumber: true })} placeholder="Optional benchmark cost" />
              <Field label="Benchmark Date">
                <input className="field" type="date" {...form.register("benchmarkDate")} />
              </Field>
              <Field label="Benchmark Source">
                <input className="field" {...form.register("benchmarkSource")} placeholder="Tamil Nadu Statistical Handbook 2022-23" />
              </Field>
            </div>
          </section>
        </main>

        <aside className="space-y-5">
          <section className="border-2 border-ink p-5">
            <h2 className="text-sm font-bold uppercase tracking-wide">Rule Preview</h2>
            <pre className="mono-value mt-4 whitespace-pre-wrap border-2 border-ink bg-gov-50 p-4 text-sm leading-7">{rulePreview}</pre>
          </section>
          <section className="border-2 border-ink p-5">
            <div className="text-xs font-bold uppercase text-muted">Benefit</div>
            <div className="mono-value mt-1 text-2xl font-bold">{formatMoneyPreview(watchedBenefitAmount)}</div>
            <div className="mt-1 text-xs font-bold uppercase text-muted">{watchedBenefitFrequency ?? "Monthly"}</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Planned Statewide Budget</div>
            <div className="mono-value mt-1 text-2xl font-bold">{formatMoneyPreview(watchedBudget)}</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Benchmark</div>
            <div className="mono-value mt-1 text-2xl font-bold">{formatCountPreview(watchedBenchmark)}</div>
          </section>
          <section className="border-2 border-ink p-5">
            <div className="text-xs font-bold uppercase text-muted">Monte Carlo</div>
            <div className="mono-value mt-1 text-2xl font-bold">{configuration.monteCarloRuns.toLocaleString("en-IN")}</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Confidence</div>
            <div className="mono-value mt-1 text-2xl font-bold">{configuration.confidenceLevel}%</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Sample Size</div>
            <div className="mono-value mt-1 text-2xl font-bold">{configuration.populationSampleSize.toLocaleString("en-IN")}</div>
          </section>
          <Button className="w-full py-4 text-base" variant="primary" icon={<Play className="h-5 w-5" />} onClick={runSimulation} disabled={createMutation.isPending}>
            Run Simulation
          </Button>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-bold uppercase tracking-wide text-ink">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  registration,
  placeholder,
  value,
  min,
  onValueChange
}: {
  label: string;
  registration?: UseFormRegisterReturn;
  placeholder?: string;
  value?: number | "";
  min?: number;
  onValueChange?: (value: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        className="field font-mono"
        type="number"
        min={min}
        placeholder={placeholder}
        value={value}
        {...registration}
        onChange={(event) => {
          registration?.onChange(event);
          const next = Number(event.target.value);
          if (onValueChange && Number.isFinite(next) && next >= (min ?? 0)) onValueChange(next);
        }}
      />
    </Field>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 border-2 border-ink px-3 py-2">
      <span className="text-sm font-bold uppercase">{label}</span>
      <input className="h-5 w-5 accent-black" type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function sanitizePolicy(policy: Policy): Policy {
  return {
    ...policy,
    budgetAllocation: optionalNumber(policy.budgetAllocation),
    benefitAmount: optionalNumber(policy.benefitAmount),
    administrativeCostPercent: optionalNumber(policy.administrativeCostPercent),
    benchmarkActualBeneficiaries: optionalNumber(policy.benchmarkActualBeneficiaries),
    benchmarkActualAnnualCost: optionalNumber(policy.benchmarkActualAnnualCost),
    benchmarkDate: policy.benchmarkDate || undefined,
    benchmarkSource: policy.benchmarkSource || undefined,
    selectedDistricts: policy.geographicScope === "Selected Districts" ? policy.selectedDistricts : []
  };
}

function optionalNumber(value: number | undefined): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function formatMoneyPreview(value: number | undefined) {
  return optionalNumber(value)?.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }) ?? "Not set";
}

function formatCountPreview(value: number | undefined) {
  return optionalNumber(value)?.toLocaleString("en-IN") ?? "Not set";
}
