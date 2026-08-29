import assert from "assert";
import fs from "fs";
import path from "path";
import XLSX from "xlsx";

const ROOT = process.cwd();

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), "utf8"));
}

function exists(relativePath) {
  assert.ok(fs.existsSync(path.join(ROOT, relativePath)), `${relativePath} should exist`);
}

exists("data/metadata/data_capability_registry.json");
exists("data/compatibility/example_policy_reports.json");
exists("data/compatibility/synthetic_population_requirements.json");
exists("reports/phase2_input_assessment.md");
exists("reports/phase2_validation_report.md");
exists("reports/phase2_summary.md");
exists("docs/policy_data_compatibility_engine.md");
exists("docs/compatibility_scoring_methodology.md");
exists("reports/policy_data_compatibility_report.xlsx");

const registry = readJson("data/metadata/data_capability_registry.json");
assert.equal(registry.state, "Tamil Nadu");
assert.ok(registry.reference_records >= 10000);
assert.ok(registry.variables.age.non_null_percentage === 100);
assert.ok(registry.variables.employment_status.sources.includes("SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR"));
assert.ok(registry.variables.disability_status.aggregate_only, "disability should be aggregate/manual-access only");

const reports = readJson("data/compatibility/example_policy_reports.json");
assert.equal(reports.length, 3);

const employment = reports.find((report) => report.policy_id === "TN_YOUTH_EMPLOYMENT_ASSISTANCE");
assert.ok(employment);
const householdIncome = employment.requirements.find((item) => item.requirement.canonical_variable === "household_income");
assert.equal(householdIncome.status, "PROXY_AVAILABLE");
assert.ok(employment.simulation_readiness === "READY_WITH_WARNINGS");
assert.ok(employment.synthetic_population_requirements.synthetic_population_requirements.approved_proxies.includes("household_income"));

const education = reports.find((report) => report.policy_id === "TN_EDUCATION_SKILLING");
assert.ok(education.reliability_score > employment.reliability_score);
assert.ok(education.simulation_readiness === "READY_WITH_WARNINGS");

const health = reports.find((report) => report.policy_id === "TN_HEALTH_INSURANCE_TOPUP");
assert.equal(health.simulation_readiness, "NOT_READY");
assert.ok(health.synthetic_population_requirements.synthetic_population_requirements.required_variables.includes("health_insurance"));
assert.ok(health.blocking_issues.some((issue) => issue.includes("disability_status")));

const phase3 = readJson("data/compatibility/synthetic_population_requirements.json");
assert.ok(phase3.TN_YOUTH_EMPLOYMENT_ASSISTANCE.synthetic_population_requirements.critical_variables.includes("age"));

const workbook = XLSX.readFile(path.join(ROOT, "reports/policy_data_compatibility_report.xlsx"));
["README", "POLICY_REQUIREMENTS", "DOMAIN_CHECK", "SCORE_BREAKDOWN", "WARNINGS", "RECOMMENDATIONS"].forEach((sheet) => {
  assert.ok(workbook.SheetNames.includes(sheet), `workbook should contain ${sheet}`);
});

console.log("Phase 2 tests passed");
