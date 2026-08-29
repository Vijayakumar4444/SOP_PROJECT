import assert from "assert";
import fs from "fs";
import path from "path";
import XLSX from "xlsx";

const ROOT = process.cwd();

function exists(relativePath) {
  assert.ok(fs.existsSync(path.join(ROOT, relativePath)), `${relativePath} should exist`);
}

function readCsv(relativePath) {
  const text = fs.readFileSync(path.join(ROOT, relativePath), "utf8").trim();
  const [headerLine, ...lines] = text.split(/\r?\n/);
  return { headers: headerLine.split(","), rows: lines };
}

const workbookPath = fs.existsSync(path.join(ROOT, "data/exports/tamil_nadu_population_reference_template_updated.xlsx"))
  ? "data/exports/tamil_nadu_population_reference_template_updated.xlsx"
  : "data/exports/tamil_nadu_population_reference_template.xlsx";
exists(workbookPath);
exists("data/processed/reference_template.csv");
exists("data/reference/template_metadata.json");
exists("data/source_registry.csv");
exists("data/reports/data_quality_checks.csv");
exists("config/canonical_schema.yaml");
exists("reports/phase1_summary.md");

const registry = readCsv("data/source_registry.csv");
assert.ok(registry.rows.length >= 5, "source registry should document at least five sources");

const template = readCsv("data/processed/reference_template.csv");
assert.ok(template.headers.includes("state"), "template should include state");
assert.ok(template.headers.includes("survey_weight"), "template should preserve survey weight contract");
assert.ok(template.headers.includes("calibrated_reference_weight_gender_ur"), "template should include phase 1 calibration weight");
assert.ok(template.rows.length >= 10000 && template.rows.length <= 30000, "template should contain 10,000-30,000 legitimate reference rows");

const metadata = JSON.parse(fs.readFileSync(path.join(ROOT, "data/reference/template_metadata.json"), "utf8"));
assert.equal(metadata.state, "Tamil Nadu");
assert.ok(metadata.actual_records >= 10000 && metadata.actual_records <= 30000);
assert.ok(metadata.available_plfs_tamil_nadu_source_rows >= metadata.actual_records);
assert.ok(metadata.sources.includes("SRC_TN_DES_GLANCE_2023_24"));
assert.ok(metadata.sources.includes("SRC_DATA_GOV_TN_GLANCE_2019"));
assert.ok(metadata.sources.includes("SRC_CENSUS_PCA_SD_2011"));
assert.ok(metadata.raw_source_files.some((item) => item.includes("tn_des")));
assert.ok(metadata.raw_source_files.some((item) => item.includes("data_gov_in")));
assert.ok(metadata.raw_source_files.some((item) => item.includes("census")));
assert.equal(metadata.quality_checks.failed, 0);

const variableDictionary = readCsv("data/reference/variable_dictionary.csv");
const variableRows = variableDictionary.rows.map((line) => line.split(","));
const ageRow = variableRows.find((row) => row[0] === "age");
const householdSizeRow = variableRows.find((row) => row[0] === "household_size");
assert.equal(ageRow?.[3], "number", "age should be typed as number");
assert.equal(householdSizeRow?.[3], "number", "household_size should be typed as number");

const quality = readCsv("data/reports/data_quality_checks.csv");
assert.ok(quality.rows.some((line) => line.includes("invalid_age_count,0,PASS")));
assert.ok(quality.rows.some((line) => line.includes("non_tamil_nadu_row_count,0,PASS")));

const workbook = XLSX.readFile(path.join(ROOT, workbookPath));
[
  "00_README",
  "01_SOURCE_REGISTRY",
  "02_VARIABLE_DICTIONARY",
  "03_REFERENCE_TEMPLATE",
  "04_STATE_MARGINALS",
  "07_GENDER_MARGINALS",
  "08_URBAN_RURAL_MARGINALS",
  "11_SOCIAL_MARGINALS",
  "12_WORKER_MARGINALS",
  "14_CALIBRATION_DIAGNOSTICS",
  "16_QUALITY_CHECKS",
].forEach((sheet) => assert.ok(workbook.SheetNames.includes(sheet), `workbook should contain ${sheet}`));

const geography = readCsv("data/calibration/current_district_geography.csv");
assert.ok(geography.rows.length >= 35, "current Tamil Nadu geography should contain PLFS district-code coverage");

exists("backend/app/modules/data_foundation/run_phase1.py");
exists("data/calibration/social_group_marginals.csv");
exists("data/calibration/worker_marginals.csv");
exists("data/calibration/calibration_diagnostics.csv");

console.log("Phase 1 tests passed");
