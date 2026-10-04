import { useMemo, useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { Database, Play, Plus, Trash2 } from "lucide-react";
import { createSimulation, startSimulationPipeline } from "../../api/simulations.api";
import { departments, ruleAttributes } from "../../constants";
import { useAppStore } from "../../stores/useAppStore";
import type { Policy, PolicyRule, RuleOperator } from "../../types";
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

  function updateRule(id: string, next: Partial<PolicyRule>) {
    setRules((current) => current.map((rule) => (rule.id === id ? { ...rule, ...next } : rule)));
  }

  function addRule() {
    setRules((current) => [...current, { id: crypto.randomUUID(), attribute: "District", operator: "=", value: "Tamil Nadu", joiner: "AND" }]);
  }

  function runSimulation() {
    setDraft(policy);
    createMutation.mutate({ policy, configuration });
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
        </main>

        <aside className="space-y-5">
          <section className="border-2 border-ink p-5">
            <h2 className="text-sm font-bold uppercase tracking-wide">Rule Preview</h2>
            <pre className="mono-value mt-4 whitespace-pre-wrap border-2 border-ink bg-gov-50 p-4 text-sm leading-7">{rulePreview}</pre>
          </section>
          <section className="border-2 border-ink p-5">
            <div className="text-xs font-bold uppercase text-muted">Monte Carlo</div>
            <div className="mono-value mt-1 text-2xl font-bold">{configuration.monteCarloRuns.toLocaleString("en-IN")}</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Confidence</div>
            <div className="mono-value mt-1 text-2xl font-bold">{configuration.confidenceLevel}%</div>
            <div className="mt-5 text-xs font-bold uppercase text-muted">Fiscal Check</div>
            <div className="mt-1 text-sm font-bold uppercase">Computed by backend</div>
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
