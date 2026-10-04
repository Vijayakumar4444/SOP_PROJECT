import type {
  BudgetRisk,
  DemographicBreakdown,
  DistrictResult,
  Policy,
  Report,
  Simulation,
  SimulationConfiguration,
  SimulationProgress,
  SimulationResult
} from "../types";

const districtNames = [
  "Chennai",
  "Coimbatore",
  "Madurai",
  "Tiruchirappalli",
  "Salem",
  "Tirunelveli",
  "Thanjavur",
  "Erode",
  "Vellore",
  "Thoothukudi",
  "Dindigul",
  "Cuddalore",
  "Kancheepuram",
  "Tiruvallur",
  "Virudhunagar",
  "Namakkal",
  "Karur",
  "Sivaganga",
  "Ramanathapuram",
  "Nilgiris"
];

export const mockDistricts: DistrictResult[] = districtNames.map((district, index) => {
  const population = 980_000 + index * 54_000;
  const coverage = 0.58 + ((index * 7) % 18) / 100;
  const beneficiaries = Math.round(population * coverage * 0.62);
  return {
    id: district.toLowerCase().replace(/\s+/g, "-"),
    district,
    population,
    eligiblePopulation: Math.round(population * 0.62),
    beneficiaries,
    coverage,
    estimatedCost: beneficiaries * 12_000,
    costPerBeneficiary: 12_000,
    equityScore: 74 + ((index * 5) % 21),
    budgetPressure: 0.38 + ((index * 3) % 24) / 100,
    ruralCoverage: coverage + (index % 2 === 0 ? 0.04 : -0.02),
    urbanCoverage: coverage + (index % 2 === 0 ? -0.02 : 0.03),
    coordinates: [78 + (index % 5) * 0.85, 8.4 + Math.floor(index / 5) * 1.3]
  };
});

export const mockSimulations: Simulation[] = [
  {
    id: "SIM-TN-2026-1042",
    policyName: "Women Household Assistance Scheme",
    department: "Social Welfare",
    date: "2026-10-03T10:12:00+05:30",
    monteCarloRuns: 50_000,
    confidenceLevel: 95,
    beneficiaryCoverage: 0.531,
    estimatedCost: 37_591_200_000,
    equityScore: 87,
    budgetRisk: "Low",
    status: "completed"
  },
  {
    id: "SIM-TN-2026-1038",
    policyName: "Rural Skill Stipend Extension",
    department: "Labour",
    date: "2026-09-29T14:42:00+05:30",
    monteCarloRuns: 25_000,
    confidenceLevel: 95,
    beneficiaryCoverage: 0.511,
    estimatedCost: 4_620_000_000,
    equityScore: 81,
    budgetRisk: "Moderate",
    status: "completed"
  },
  {
    id: "SIM-TN-2026-1027",
    policyName: "Senior Citizen Pension Revision",
    department: "Social Welfare",
    date: "2026-09-18T09:16:00+05:30",
    monteCarloRuns: 100_000,
    confidenceLevel: 99,
    beneficiaryCoverage: 0.423,
    estimatedCost: 7_180_000_000,
    equityScore: 78,
    budgetRisk: "High",
    status: "completed"
  },
  {
    id: "SIM-TN-2026-1011",
    policyName: "Farm Household Irrigation Support",
    department: "Agriculture",
    date: "2026-09-08T16:20:00+05:30",
    monteCarloRuns: 10_000,
    confidenceLevel: 90,
    beneficiaryCoverage: 0.372,
    estimatedCost: 3_020_000_000,
    equityScore: 73,
    budgetRisk: "Moderate",
    status: "completed"
  }
];

export const mockDemographics: DemographicBreakdown = {
  gender: [
    { category: "Female", value: 0.89 },
    { category: "Male", value: 0.1 },
    { category: "Other", value: 0.01 }
  ],
  socialGroup: [
    { category: "SC", beneficiaries: 1_820_000, coverage: 0.71 },
    { category: "ST", beneficiaries: 382_000, coverage: 0.69 },
    { category: "OBC", beneficiaries: 3_910_000, coverage: 0.68 },
    { category: "General", beneficiaries: 1_260_000, coverage: 0.61 }
  ],
  ruralUrban: [
    { category: "Rural", beneficiaries: 5_220_000, nonBeneficiaries: 2_010_000 },
    { category: "Urban", beneficiaries: 3_021_034, nonBeneficiaries: 1_797_429 }
  ],
  ageGroup: [
    { category: "18-25", value: 980_000 },
    { category: "26-35", value: 2_220_000 },
    { category: "36-45", value: 2_640_000 },
    { category: "46-60", value: 2_401_034 },
    { category: "60+", value: 0 }
  ],
  incomeGroup: [
    { category: "< ₹1L", value: 2_430_000 },
    { category: "₹1L-₹1.5L", value: 2_870_000 },
    { category: "₹1.5L-₹2L", value: 1_920_000 },
    { category: "₹2L-₹2.5L", value: 1_021_034 }
  ]
};

export const mockResult: SimulationResult = {
  simulation: mockSimulations[0],
  timestamp: "2026-10-03T10:27:00+05:30",
  beneficiary: {
    coverage: 0.531,
    beneficiaries: 3_132_600,
    targetFit: 100,
    basePopulation: 12_048_463,
    targetShare: 0.49,
    targetUniverse: "Women synthetic population",
    eligiblePopulation: 3_132_600,
    nonEligiblePopulation: 2_771_147,
    targetPopulation: 5_903_747
  },
  budget: {
    allocatedBudget: 12_000_000_000,
    meanCost: 9_840_000_000,
    unusedBudget: 2_160_000_000,
    costPerBeneficiary: 11_940,
    probabilityOverrun: 0.037,
    worstCaseCost: 10_630_000_000,
    utilization: 0.82,
    riskScore: 23,
    riskLevel: "Low"
  },
  monteCarlo: {
    mean: 9_840_000_000,
    median: 9_790_000_000,
    p5: 9_240_000_000,
    p95: 10_630_000_000,
    budget: 12_000_000_000,
    overrunProbability: 0.037,
    buckets: Array.from({ length: 16 }, (_, index) => ({
      lower: 8_900_000_000 + index * 130_000_000,
      upper: 9_030_000_000 + index * 130_000_000,
      frequency: Math.round(800 + 4_100 * Math.exp(-Math.pow(index - 7, 2) / 18))
    }))
  },
  confidenceIntervals: [
    { metric: "Beneficiaries", lower: 8_010_000, estimate: 8_241_034, upper: 8_470_000, formatter: "number" },
    { metric: "Policy Cost", lower: 9_240_000_000, estimate: 9_840_000_000, upper: 10_630_000_000, formatter: "currency" },
    { metric: "Coverage", lower: 0.661, estimate: 0.684, upper: 0.702, formatter: "percent" },
    { metric: "District Coverage", lower: 0.58, estimate: 0.67, upper: 0.76, formatter: "percent" }
  ],
  demographics: mockDemographics,
  districts: mockDistricts,
  equity: {
    overall: 87,
    gender: 92,
    socialGroup: 84,
    ruralUrban: 89,
    district: 78,
    income: 91,
    explanation:
      "Scores compare eligible population reach across demographic strata and penalize large coverage gaps between comparable groups."
  },
  interpretation: {
    classification: "Success",
    summary:
      "The policy achieves broad beneficiary coverage while remaining within the allocated budget across most Monte Carlo scenarios. Coverage is comparatively strong among rural households, while a small set of districts show lower-than-average reach.",
    strengths: ["High eligible population coverage", "Stable projected expenditure", "Strong rural inclusion"],
    concerns: [
      "Lower coverage in specific districts requires implementation review",
      "Extreme scenarios still create a modest overrun probability",
      "District equity remains the weakest submetric"
    ]
  },
  sensitivity: [
    { variable: "Income Threshold", beneficiaryImpact: 12.1, costImpact: 13.8, equityImpact: 5.2 },
    { variable: "Age Upper Bound", beneficiaryImpact: 8.4, costImpact: 7.9, equityImpact: 3.1 },
    { variable: "Benefit Amount", beneficiaryImpact: 1.5, costImpact: 15.4, equityImpact: 0.8 },
    { variable: "District Scope", beneficiaryImpact: 6.7, costImpact: 8.1, equityImpact: 9.4 },
    { variable: "Rural Eligibility", beneficiaryImpact: 4.6, costImpact: 4.3, equityImpact: 10.7 }
  ]
};

export const mockReports: Report[] = [
  {
    id: "RPT-9821",
    name: "Women Household Assistance Scheme Assessment",
    category: "Policy Assessment Reports",
    simulationId: "SIM-TN-2026-1042",
    generatedAt: "2026-10-03T10:36:00+05:30",
    format: "PDF",
    size: "4.8 MB"
  },
  {
    id: "RPT-9817",
    name: "District Equity Appendix",
    category: "District Reports",
    simulationId: "SIM-TN-2026-1042",
    generatedAt: "2026-10-03T10:37:00+05:30",
    format: "CSV",
    size: "720 KB"
  },
  {
    id: "RPT-9730",
    name: "Fiscal Risk Monte Carlo Output",
    category: "Fiscal Risk Reports",
    simulationId: "SIM-TN-2026-1038",
    generatedAt: "2026-09-29T15:10:00+05:30",
    format: "XLSX",
    size: "2.1 MB"
  }
];

const progressStartTimes = new Map<string, number>();
const simulationInputs = new Map<string, { policy: Policy; configuration: SimulationConfiguration; createdAt: string }>();

export function resetMockProgress(id: string) {
  progressStartTimes.set(id, Date.now());
}

export function registerMockSimulation(id: string, policy: Policy, configuration: SimulationConfiguration) {
  simulationInputs.set(id, { policy, configuration, createdAt: new Date().toISOString() });
  resetMockProgress(id);
}

export function mockProgress(id: string): SimulationProgress {
  if (!progressStartTimes.has(id)) {
    progressStartTimes.set(id, Date.now());
  }

  const startedAt = progressStartTimes.get(id) ?? Date.now();
  const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
  const progress = Math.min(100, Math.max(4, Math.floor((elapsedSeconds / 18) * 100)));
  const completedIterations = Math.min(50_000, Math.floor((progress / 100) * 50_000));

  return {
    simulationId: id,
    policyName: simulationInputs.get(id)?.policy.name ?? "Women Household Assistance Scheme",
    progress,
    currentStage: progress >= 100 ? "Recommendation Engine" : "Backend Architecture Flow",
    completedIterations,
    totalIterations: 50_000,
    elapsedSeconds,
    stages: [
      { label: "DATA FOUNDATION", status: progress > 12 ? "complete" : "active" },
      { label: "POLICY-DATA COMPATIBILITY ENGINE", status: progress > 25 ? "complete" : progress > 12 ? "active" : "pending" },
      { label: "SYNTHETIC POPULATION GENERATION", status: progress > 37 ? "complete" : progress > 25 ? "active" : "pending" },
      { label: "POPULATION VALIDATION", status: progress > 50 ? "complete" : progress > 37 ? "active" : "pending" },
      { label: "CALIBRATION & REWEIGHTING", status: progress > 62 ? "complete" : progress > 50 ? "active" : "pending" },
      { label: "POLICY ENGINE", status: progress > 75 ? "complete" : progress > 62 ? "active" : "pending" },
      { label: "MONTE CARLO & UNCERTAINTY ENGINE", status: progress > 87 ? "complete" : progress > 75 ? "active" : "pending" },
      { label: "RECOMMENDATION ENGINE", status: progress >= 100 ? "complete" : progress > 87 ? "active" : "pending" }
    ]
  };
}

export function generateMockResult(id: string): SimulationResult {
  const input = simulationInputs.get(id);
  if (!input) return { ...mockResult, simulation: { ...mockResult.simulation, id } };

  const { policy, configuration, createdAt } = input;
  const rulesText = `${policy.description} ${policy.rules.map((rule) => `${rule.attribute} ${rule.operator} ${rule.value}`).join(" ")}`.toLowerCase();
  const ruleAttributes = policy.rules.map((rule) => rule.attribute.toLowerCase());
  const annualBenefit = extractAnnualBenefit(policy.description);
  const basePopulation = 12_048_463;
  const targetUniverse = estimateTargetUniverse(rulesText, ruleAttributes, basePopulation);
  const fullPopulationCoverage = clamp(estimateCoverage(rulesText, ruleAttributes, policy.rules.length), 0.08, 0.96);
  const coverage = clamp(fullPopulationCoverage / targetUniverse.share, 0.03, 0.98);
  const targetFit = estimateTargetFit(rulesText, ruleAttributes, policy.rules.length, coverage);
  const targetPopulation = targetUniverse.population;
  const beneficiaries = Math.round(targetPopulation * coverage);
  const meanCost = Math.round(beneficiaries * annualBenefit);
  const planningEnvelope = estimatePlanningEnvelope(fullPopulationCoverage, annualBenefit, basePopulation);
  const utilization = meanCost / Math.max(planningEnvelope, 1);
  const probabilityOverrun = clamp((utilization - 0.9) / 1.1, 0.01, 0.99);
  const riskScore = Math.round(clamp(utilization * 34 + coverage * 12 + (policy.rules.length <= 2 ? 14 : 0), 4, 100));
  const riskLevel = riskScore >= 75 ? "Critical" : riskScore >= 55 ? "High" : riskScore >= 30 ? "Moderate" : "Low";
  const equity = estimateEquity(rulesText, coverage, riskScore);
  const classification = classifyPolicy(coverage, targetFit, utilization, riskScore, equity.overall);
  const districts = generateDistrictResults(coverage, annualBenefit, equity.district);
  const demographics = generateDemographics(rulesText, beneficiaries, coverage);
  const p5 = Math.round(meanCost * (0.88 - riskScore / 1000));
  const p95 = Math.round(meanCost * (1.08 + riskScore / 420));

  return {
    simulation: {
      id,
      policyName: policy.name,
      department: policy.department,
      date: createdAt,
      monteCarloRuns: configuration.monteCarloRuns,
      confidenceLevel: configuration.confidenceLevel,
      beneficiaryCoverage: coverage,
      estimatedCost: meanCost,
      equityScore: equity.overall,
      budgetRisk: riskLevel,
      status: "completed"
    },
    timestamp: new Date().toISOString(),
    beneficiary: {
      coverage,
      beneficiaries,
      targetFit,
      basePopulation,
      targetShare: targetUniverse.share,
      targetUniverse: targetUniverse.label,
      eligiblePopulation: beneficiaries,
      nonEligiblePopulation: targetPopulation - beneficiaries,
      targetPopulation
    },
    budget: {
      allocatedBudget: planningEnvelope,
      meanCost,
      unusedBudget: planningEnvelope - meanCost,
      costPerBeneficiary: Math.round(meanCost / Math.max(beneficiaries, 1)),
      probabilityOverrun,
      worstCaseCost: p95,
      utilization,
      riskScore,
      riskLevel
    },
    monteCarlo: {
      mean: meanCost,
      median: Math.round(meanCost * 0.985),
      p5,
      p95,
      budget: planningEnvelope,
      overrunProbability: probabilityOverrun,
      buckets: Array.from({ length: 16 }, (_, index) => {
        const centerOffset = index - 7.5;
        const lower = Math.round(meanCost * (0.78 + index * 0.035));
        return {
          lower,
          upper: Math.round(lower + meanCost * 0.035),
          frequency: Math.round(500 + 4_400 * Math.exp(-Math.pow(centerOffset, 2) / (10 + riskScore / 8)))
        };
      })
    },
    confidenceIntervals: [
      { metric: "Beneficiaries", lower: Math.round(beneficiaries * 0.95), estimate: beneficiaries, upper: Math.round(beneficiaries * 1.05), formatter: "number" },
      { metric: "Policy Cost", lower: p5, estimate: meanCost, upper: p95, formatter: "currency" },
      { metric: "Coverage", lower: clamp(coverage - 0.035, 0, 1), estimate: coverage, upper: clamp(coverage + 0.035, 0, 1), formatter: "percent" },
      { metric: "District Coverage", lower: Math.min(...districts.map((district) => district.coverage)), estimate: coverage, upper: Math.max(...districts.map((district) => district.coverage)), formatter: "percent" }
    ],
    demographics,
    districts,
    equity,
    interpretation: {
      classification,
      summary: buildSummary(classification, utilization, coverage, targetFit),
      strengths: classification === "Failure" ? ["Broad reach is technically achievable"] : ["Coverage aligns with stated eligibility", "Simulation completes within configured confidence level"],
      concerns: buildConcerns(classification, utilization, riskScore)
    },
    sensitivity: [
      { variable: "Income Threshold", beneficiaryImpact: Math.round(coverage * 18), costImpact: Math.round(utilization * 11), equityImpact: 6.2 },
      { variable: "Benefit Amount", beneficiaryImpact: 2.1, costImpact: Math.round(utilization * 18), equityImpact: 1.1 },
      { variable: "District Scope", beneficiaryImpact: 7.8, costImpact: 8.4, equityImpact: Math.round((100 - equity.district) / 4) },
      { variable: "Rural Eligibility", beneficiaryImpact: 5.3, costImpact: 4.8, equityImpact: 9.7 }
    ]
  };
}

function estimateCoverage(text: string, attributes: string[], ruleCount: number): number {
  let coverage = text.includes("every household") || text.includes("all household") || text.includes("universal") ? 0.91 : 0.72;
  if (attributes.includes("gender")) coverage -= 0.2;
  if (attributes.includes("age")) coverage -= 0.1;
  if (attributes.includes("household income") || attributes.includes("annual income")) coverage -= 0.16;
  if (attributes.includes("disability status")) coverage -= 0.35;
  if (attributes.includes("employment status")) coverage -= 0.12;
  if (attributes.includes("district")) coverage -= 0.08;
  if (text.includes("rural only")) coverage -= 0.18;
  if (text.includes("urban only")) coverage -= 0.28;
  if (ruleCount <= 2) coverage += 0.07;
  return coverage;
}

function estimateTargetUniverse(text: string, attributes: string[], basePopulation: number): { population: number; share: number; label: string } {
  let share = 1;
  const labels: string[] = [];

  if (attributes.includes("gender") || text.includes("women") || text.includes("female")) {
    share *= 0.49;
    labels.push("women");
  }
  if (text.includes("rural only")) {
    share *= 0.57;
    labels.push("rural residents");
  }
  if (text.includes("urban only")) {
    share *= 0.43;
    labels.push("urban residents");
  }
  if (attributes.includes("disability status")) {
    share *= 0.08;
    labels.push("persons with disability");
  }
  if (attributes.includes("employment status")) {
    share *= 0.18;
    labels.push("employment-status target group");
  }
  if (attributes.includes("district")) {
    share *= 0.55;
    labels.push("selected-district population");
  }

  if (labels.length === 0) {
    return { population: basePopulation, share: 1, label: "Total synthetic population" };
  }

  const label = `${labels.join(" + ").replace(/\b\w/g, (letter) => letter.toUpperCase())} synthetic population`;
  return { population: Math.round(basePopulation * share), share, label };
}

function estimateTargetFit(text: string, attributes: string[], ruleCount: number, coverage: number): number {
  let targetedSignals = 0;
  if (attributes.includes("gender")) targetedSignals += 1;
  if (attributes.includes("age")) targetedSignals += 1;
  if (attributes.includes("household income") || attributes.includes("annual income") || text.includes("income")) targetedSignals += 1;
  if (attributes.includes("disability status")) targetedSignals += 2;
  if (attributes.includes("employment status")) targetedSignals += 1;
  if (attributes.includes("district") || text.includes("rural only") || text.includes("urban only")) targetedSignals += 1;

  const universal = text.includes("every household") || text.includes("all household") || text.includes("universal");
  const benchmark = universal && targetedSignals === 0 ? 0.7 : targetedSignals >= 4 ? 0.18 : targetedSignals >= 3 ? 0.22 : targetedSignals === 2 ? 0.3 : targetedSignals === 1 ? 0.42 : 0.6;
  let score = 72 + (coverage - benchmark) * 110;
  if (text.includes("income")) score += 8;
  if (ruleCount <= 2 && !universal) score -= 8;
  return Math.round(clamp(score, 0, 100));
}

function extractAnnualBenefit(description: string): number {
  const normalized = description.replace(/,/g, "");
  const benefitMatch = normalized.match(/(?:assistance|benefit|transfer|stipend|pension|subsidy)(?:\s+\w+){0,4}\s+(?:of\s+)?(?:rs|₹|inr)\s*(\d+)/i);
  const amounts = [...normalized.matchAll(/(?:rs|₹|inr)\s*(\d+)/gi)].map((match) => Number(match[1])).filter(Boolean);
  const amount = benefitMatch ? Number(benefitMatch[1]) : amounts.length ? amounts[0] : 1_000;
  const monthly = /monthly|per month|month/.test(description.toLowerCase());
  return monthly ? amount * 12 : amount;
}

function estimateEquity(text: string, coverage: number, riskScore: number) {
  const universal = text.includes("every household") || text.includes("universal");
  const gender = text.includes("female") || text.includes("women") ? 74 : universal ? 88 : 84;
  const socialGroup = text.includes("social group") || universal ? 82 : 76;
  const ruralUrban = text.includes("rural only") || text.includes("urban only") ? 58 : 84;
  const district = coverage > 0.85 ? 70 : 78;
  const income = text.includes("income") ? 88 : 62;
  const overall = Math.round(clamp((gender + socialGroup + ruralUrban + district + income) / 5 - riskScore * 0.08, 35, 94));
  return {
    overall,
    gender,
    socialGroup,
    ruralUrban,
    district,
    income,
    explanation: "Scores are generated from the submitted eligibility rules, coverage breadth, income targeting and fiscal risk."
  };
}

function classifyPolicy(coverage: number, targetFit: number, utilization: number, riskScore: number, equityScore: number): SimulationResult["interpretation"]["classification"] {
  const fiscalSustainability = fiscalSustainabilityScore(utilization);
  const score = targetFit * 0.3 + equityScore * 0.3 + fiscalSustainability * 0.25 + (100 - riskScore) * 0.15;

  if (targetFit < 35 || equityScore < 45 || fiscalSustainability < 20 || riskScore >= 82) return "Failure";
  if (coverage < 0.1 && targetFit < 55) return "Failure";
  if (score >= 75 && targetFit >= 65 && equityScore >= 65 && fiscalSustainability >= 60 && riskScore < 55) return "Success";
  if (score >= 55 && targetFit >= 45 && equityScore >= 55 && fiscalSustainability >= 25 && riskScore < 75) return "Moderate";
  return "Failure";
}

function fiscalSustainabilityScore(utilization: number): number {
  return clamp(100 - Math.max(0, utilization - 0.7) * 150, 0, 100);
}

function estimatePlanningEnvelope(coverage: number, annualBenefit: number, targetPopulation: number): number {
  const expectedPolicyScale = targetPopulation * Math.max(coverage, 0.12) * annualBenefit;
  const multiplier = coverage >= 0.75 ? 0.55 : coverage >= 0.45 ? 0.85 : 1.35;
  return Math.round(expectedPolicyScale * multiplier);
}

function generateDistrictResults(coverage: number, annualBenefit: number, districtEquity: number): DistrictResult[] {
  return districtNames.map((district, index) => {
    const population = 980_000 + index * 54_000;
    const localCoverage = clamp(coverage + (((index * 11) % 17) - 8) / 100, 0.03, 0.98);
    const beneficiaries = Math.round(population * localCoverage * 0.62);
    const estimatedCost = beneficiaries * annualBenefit;
    return {
      id: district.toLowerCase().replace(/\s+/g, "-"),
      district,
      population,
      eligiblePopulation: Math.round(population * 0.62),
      beneficiaries,
      coverage: localCoverage,
      estimatedCost,
      costPerBeneficiary: annualBenefit,
      equityScore: Math.round(clamp(districtEquity + (((index * 7) % 19) - 9), 30, 96)),
      budgetPressure: clamp(localCoverage * annualBenefit / 18_000, 0.08, 1),
      ruralCoverage: clamp(localCoverage + (index % 2 === 0 ? 0.04 : -0.03), 0, 1),
      urbanCoverage: clamp(localCoverage + (index % 2 === 0 ? -0.03 : 0.03), 0, 1),
      coordinates: [78 + (index % 5) * 0.85, 8.4 + Math.floor(index / 5) * 1.3]
    };
  });
}

function generateDemographics(text: string, beneficiaries: number, coverage: number): DemographicBreakdown {
  const femaleFocused = text.includes("female") || text.includes("women");
  const ruralFocused = text.includes("rural");
  return {
    gender: [
      { category: "Female", value: femaleFocused ? 0.9 : 0.49 },
      { category: "Male", value: femaleFocused ? 0.09 : 0.5 },
      { category: "Other", value: 0.01 }
    ],
    socialGroup: [
      { category: "SC", beneficiaries: Math.round(beneficiaries * 0.22), coverage: clamp(coverage + 0.02, 0, 1) },
      { category: "ST", beneficiaries: Math.round(beneficiaries * 0.05), coverage: clamp(coverage - 0.03, 0, 1) },
      { category: "OBC", beneficiaries: Math.round(beneficiaries * 0.48), coverage },
      { category: "General", beneficiaries: Math.round(beneficiaries * 0.25), coverage: clamp(coverage - 0.06, 0, 1) }
    ],
    ruralUrban: [
      { category: "Rural", beneficiaries: Math.round(beneficiaries * (ruralFocused ? 0.78 : 0.57)), nonBeneficiaries: Math.round(beneficiaries * 0.24) },
      { category: "Urban", beneficiaries: Math.round(beneficiaries * (ruralFocused ? 0.22 : 0.43)), nonBeneficiaries: Math.round(beneficiaries * 0.19) }
    ],
    ageGroup: [
      { category: "18-25", value: Math.round(beneficiaries * 0.13) },
      { category: "26-35", value: Math.round(beneficiaries * 0.27) },
      { category: "36-45", value: Math.round(beneficiaries * 0.28) },
      { category: "46-60", value: Math.round(beneficiaries * 0.24) },
      { category: "60+", value: Math.round(beneficiaries * 0.08) }
    ],
    incomeGroup: [
      { category: "< Rs 1L", value: Math.round(beneficiaries * 0.32) },
      { category: "Rs 1L-Rs 1.5L", value: Math.round(beneficiaries * 0.3) },
      { category: "Rs 1.5L-Rs 2L", value: Math.round(beneficiaries * 0.22) },
      { category: "Rs 2L-Rs 2.5L", value: Math.round(beneficiaries * 0.16) }
    ]
  };
}

function buildSummary(classification: SimulationResult["interpretation"]["classification"], utilization: number, coverage: number, targetFit: number): string {
  if (classification === "Failure") return "Backend appraisal shows weak real-world feasibility because targeting, equity, fiscal pressure or risk is outside acceptable limits.";
  if (classification === "Moderate") {
    return `The policy is implementable, but one or more metrics need review: coverage ${(coverage * 100).toFixed(1)}%, target fit ${targetFit}/100, fiscal pressure ${(utilization * 100).toFixed(1)}%.`;
  }
  return `The policy has strong real-world alignment: coverage ${(coverage * 100).toFixed(1)}%, target fit ${targetFit}/100, and manageable fiscal pressure.`;
}

function buildConcerns(classification: SimulationResult["interpretation"]["classification"], utilization: number, riskScore: number): string[] {
  if (classification === "Failure") return ["Targeting or equity is too weak", "Fiscal pressure or uncertainty risk is too high", "Eligibility or benefit design needs revision"];
  return utilization > 0.85 || riskScore > 55 ? ["Monitor district fiscal pressure", "Review p95 cost before approval"] : ["No major critical concerns detected"];
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
