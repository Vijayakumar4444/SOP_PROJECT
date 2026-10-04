import { apiClient, useMockApi } from "./axios";
import { defaultRules } from "../constants";
import type { Policy, PolicyRule, ValidationResult } from "../types";

const wait = (ms = 250) => new Promise((resolve) => window.setTimeout(resolve, ms));

export async function validatePolicy(policy: Policy): Promise<ValidationResult> {
  if (useMockApi) {
    await wait();
    const checks = [
      { label: "Policy name configured", valid: policy.name.trim().length > 3 },
      { label: "Policy description supplied", valid: policy.description.trim().length > 20 },
      { label: "Policy rules valid", valid: policy.rules.every((rule) => rule.attribute && rule.operator && rule.value) },
      { label: "Backend fiscal model available", valid: true },
      {
        label: "District scope valid",
        valid: policy.geographicScope !== "Selected Districts" || policy.selectedDistricts.length > 0,
        detail: policy.geographicScope === "Selected Districts" ? "At least one district is required." : undefined
      },
      { label: "Population dataset available", valid: true }
    ];
    return { valid: checks.every((check) => check.valid), checks };
  }
  const { data } = await apiClient.post<ValidationResult>("/policies/validate", policy);
  return data;
}

export async function parsePolicyDescription(description: string): Promise<PolicyRule[]> {
  if (useMockApi) {
    await wait(500);
    return defaultRules.map((rule) => ({ ...rule, id: crypto.randomUUID() }));
  }
  const { data } = await apiClient.post<PolicyRule[]>("/policies/parse", { description });
  return data;
}
