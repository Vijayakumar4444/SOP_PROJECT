export type Department =
  | "Social Welfare"
  | "Rural Development"
  | "Education"
  | "Health"
  | "Agriculture"
  | "Labour"
  | "Housing"
  | "Other";

export type GeographicScope = "Tamil Nadu" | "Selected Districts" | "Rural Only" | "Urban Only";
export type RuleOperator = "=" | "!=" | ">" | "<" | ">=" | "<=" | "IN" | "NOT IN" | "BETWEEN";
export type RuleJoiner = "AND" | "OR";
export type SimulationStatus = "draft" | "queued" | "running" | "completed" | "failed";
export type BudgetRisk = "Low" | "Moderate" | "High" | "Critical";

export interface PolicyRule {
  id: string;
  attribute: string;
  operator: RuleOperator;
  value: string;
  joiner: RuleJoiner;
}

export interface Policy {
  id?: string;
  name: string;
  department: Department;
  description: string;
  objectives?: string;
  budgetAllocation?: number;
  geographicScope: GeographicScope;
  selectedDistricts: string[];
  rules: PolicyRule[];
}

export interface SimulationConfiguration {
  monteCarloRuns: number;
  confidenceLevel: 90 | 95 | 99;
  randomSeed?: number;
  populationSampleSize: number;
  budgetConstraint: boolean;
  sensitivityAnalysis: boolean;
}

export interface Simulation {
  id: string;
  policyName: string;
  department: Department;
  date: string;
  monteCarloRuns: number;
  confidenceLevel: 90 | 95 | 99;
  beneficiaryCoverage: number;
  estimatedCost: number;
  equityScore: number;
  budgetRisk: BudgetRisk;
  status: SimulationStatus;
}

export interface SimulationProgress {
  simulationId: string;
  policyName: string;
  progress: number;
  currentStage: string;
  completedIterations: number;
  totalIterations: number;
  elapsedSeconds: number;
  stages: Array<{ label: string; status: "complete" | "active" | "pending" | "failed"; progress?: number }>;
}

export interface BeneficiarySummary {
  coverage: number;
  beneficiaries: number;
  targetFit: number;
  basePopulation: number;
  targetShare: number;
  targetUniverse: string;
  eligiblePopulation: number;
  nonEligiblePopulation: number;
  targetPopulation: number;
}

export interface BudgetSummary {
  allocatedBudget: number;
  meanCost: number;
  unusedBudget: number;
  costPerBeneficiary: number;
  probabilityOverrun: number;
  worstCaseCost: number;
  utilization: number;
  riskScore: number;
  riskLevel: BudgetRisk;
}

export interface MonteCarloBucket {
  lower: number;
  upper: number;
  frequency: number;
}

export interface MonteCarloResult {
  mean: number;
  median: number;
  p5: number;
  p95: number;
  budget: number;
  overrunProbability: number;
  buckets: MonteCarloBucket[];
}

export interface ConfidenceInterval {
  metric: string;
  lower: number;
  estimate: number;
  upper: number;
  formatter: "number" | "currency" | "percent";
}

export interface DemographicBreakdown {
  gender: Array<{ category: string; value: number }>;
  socialGroup: Array<{ category: string; beneficiaries: number; coverage: number }>;
  ruralUrban: Array<{ category: string; beneficiaries: number; nonBeneficiaries: number }>;
  ageGroup: Array<{ category: string; value: number }>;
  incomeGroup: Array<{ category: string; value: number }>;
}

export interface DistrictResult {
  id: string;
  district: string;
  population: number;
  eligiblePopulation: number;
  beneficiaries: number;
  coverage: number;
  estimatedCost: number;
  costPerBeneficiary: number;
  equityScore: number;
  budgetPressure: number;
  ruralCoverage: number;
  urbanCoverage: number;
  coordinates: [number, number];
}

export interface EquityMetrics {
  overall: number;
  gender: number;
  socialGroup: number;
  ruralUrban: number;
  district: number;
  income: number;
  explanation: string;
}

export interface PolicyInterpretation {
  classification: "Success" | "Moderate" | "Failure";
  summary: string;
  strengths: string[];
  concerns: string[];
}

export interface SimulationResult {
  simulation: Simulation;
  timestamp: string;
  beneficiary: BeneficiarySummary;
  budget: BudgetSummary;
  monteCarlo: MonteCarloResult;
  confidenceIntervals: ConfidenceInterval[];
  demographics: DemographicBreakdown;
  districts: DistrictResult[];
  equity: EquityMetrics;
  interpretation: PolicyInterpretation;
  sensitivity: Array<{ variable: string; beneficiaryImpact: number; costImpact: number; equityImpact: number }>;
}

export interface SimulationComparison {
  simulations: Simulation[];
  metrics: Array<{ metric: string; values: Array<{ id: string; value: number }>; formatter: "percent" | "currency" | "number" }>;
}

export interface Report {
  id: string;
  name: string;
  category: string;
  simulationId: string;
  generatedAt: string;
  format: "PDF" | "CSV" | "PBIX" | "XLSX";
  size: string;
}

export interface ValidationResult {
  valid: boolean;
  checks: Array<{ label: string; valid: boolean; detail?: string }>;
}
