import { create } from "zustand";
import { defaultRules } from "../constants";
import type { Policy, SimulationConfiguration } from "../types";

interface AppState {
  sidebarCollapsed: boolean;
  comparisonSelection: string[];
  policyDraft: Policy;
  configuration: SimulationConfiguration;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setPolicyDraft: (policy: Policy) => void;
  setConfiguration: (configuration: SimulationConfiguration) => void;
  toggleComparisonSelection: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  comparisonSelection: ["SIM-TN-2026-1042", "SIM-TN-2026-1038"],
  policyDraft: {
    name: "Women Household Assistance Scheme",
    department: "Social Welfare",
    description:
      "Provide monthly financial assistance of Rs 1,000 to eligible women aged 21-60 belonging to households with annual income below Rs 2.5 lakh.",
    objectives: "Improve household financial resilience and inclusion among low-income women.",
    geographicScope: "Tamil Nadu",
    selectedDistricts: [],
    rules: defaultRules
  },
  configuration: {
    monteCarloRuns: 50_000,
    confidenceLevel: 95,
    populationSampleSize: 12_000,
    budgetConstraint: true,
    sensitivityAnalysis: true
  },
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setPolicyDraft: (policyDraft) => set({ policyDraft }),
  setConfiguration: (configuration) => set({ configuration }),
  toggleComparisonSelection: (id) =>
    set((state) => {
      const exists = state.comparisonSelection.includes(id);
      if (exists) return { comparisonSelection: state.comparisonSelection.filter((item) => item !== id) };
      if (state.comparisonSelection.length >= 4) return state;
      return { comparisonSelection: [...state.comparisonSelection, id] };
    })
}));
