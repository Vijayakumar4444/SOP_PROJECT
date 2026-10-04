import { apiClient, useMockApi } from "./axios";
import { generateMockResult, mockProgress, mockSimulations, registerMockSimulation } from "./mockData";
import type {
  Policy,
  Simulation,
  SimulationComparison,
  SimulationConfiguration,
  SimulationProgress,
  SimulationResult
} from "../types";

const wait = (ms = 300) => new Promise((resolve) => window.setTimeout(resolve, ms));

export async function listSimulations(): Promise<Simulation[]> {
  if (useMockApi) {
    await wait();
    return mockSimulations;
  }
  const { data } = await apiClient.get<Simulation[]>("/simulations");
  return data;
}

export async function createSimulation(payload: {
  policy: Policy;
  configuration: SimulationConfiguration;
}): Promise<{ simulationId: string }> {
  if (useMockApi) {
    await wait(450);
    const simulationId = `SIM-TN-${Date.now().toString().slice(-6)}`;
    registerMockSimulation(simulationId, payload.policy, payload.configuration);
    return { simulationId };
  }
  const { data } = await apiClient.post<{ simulationId: string }>("/simulations", payload);
  return data;
}

export async function startSimulationPipeline(id: string): Promise<{ simulationId: string; status: string }> {
  if (useMockApi) {
    await wait();
    return { simulationId: id, status: "queued" };
  }
  const { data } = await apiClient.post<{ simulationId: string; status: string }>(`/simulations/${id}/pipeline`);
  return data;
}

export async function getSimulationProgress(id: string): Promise<SimulationProgress> {
  if (useMockApi) {
    await wait();
    return mockProgress(id);
  }
  const { data } = await apiClient.get<SimulationProgress>(`/simulations/${id}/progress`);
  return data;
}

export async function getSimulationResult(id: string): Promise<SimulationResult> {
  if (useMockApi) {
    await wait();
    return generateMockResult(id);
  }
  const { data } = await apiClient.get<SimulationResult>(`/simulations/${id}/results`);
  return data;
}

export async function compareSimulations(ids: string[]): Promise<SimulationComparison> {
  if (useMockApi) {
    await wait();
    const simulations = mockSimulations.filter((simulation) => ids.includes(simulation.id));
    return {
      simulations,
      metrics: [
        {
          metric: "Beneficiary Coverage",
          formatter: "percent",
          values: simulations.map((simulation) => ({ id: simulation.id, value: simulation.beneficiaryCoverage }))
        },
        {
          metric: "Estimated Cost",
          formatter: "currency",
          values: simulations.map((simulation) => ({ id: simulation.id, value: simulation.estimatedCost }))
        },
        {
          metric: "Equity Score",
          formatter: "number",
          values: simulations.map((simulation) => ({ id: simulation.id, value: simulation.equityScore }))
        }
      ]
    };
  }
  const { data } = await apiClient.post<SimulationComparison>("/simulations/compare", { ids });
  return data;
}
