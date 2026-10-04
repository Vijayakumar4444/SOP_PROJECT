import jsPDF from "jspdf";
import type { SimulationResult } from "../types";
import { formatCompactNumber, formatCurrency, formatPercent } from "./format";

function pdfText(value: string): string {
  return value.replace(/₹/g, "Rs ");
}

function addSection(doc: jsPDF, title: string, y: number): number {
  doc.setFillColor(232, 245, 233);
  doc.rect(14, y, 182, 8, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(0, 0, 0);
  doc.text(title.toUpperCase(), 18, y + 5.5);
  return y + 14;
}

function addKeyValue(doc: jsPDF, label: string, value: string, x: number, y: number, width = 56): void {
  doc.setDrawColor(20, 20, 20);
  doc.roundedRect(x, y, width, 20, 1.5, 1.5);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7);
  doc.setTextColor(90, 90, 90);
  doc.text(label.toUpperCase(), x + 3, y + 6, { maxWidth: width - 6 });
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(0, 0, 0);
  doc.text(pdfText(value), x + 3, y + 15, { maxWidth: width - 6 });
}

function addList(doc: jsPDF, items: string[], x: number, y: number): number {
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  let nextY = y;
  items.forEach((item) => {
    const lines = doc.splitTextToSize(`- ${item}`, 170);
    doc.text(lines, x, nextY);
    nextY += lines.length * 5;
  });
  return nextY;
}

export function exportSimulationPdf(result: SimulationResult): void {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const generatedAt = new Date(result.timestamp).toLocaleString("en-IN");

  doc.setFillColor(22, 163, 74);
  doc.rect(0, 0, 210, 24, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(17);
  doc.text("PolicySim TN - Simulation Report", 14, 11);
  doc.setFontSize(9);
  doc.text(`Generated: ${generatedAt}`, 14, 18);

  doc.setTextColor(0, 0, 0);
  doc.setFontSize(16);
  doc.text(result.simulation.policyName, 14, 36, { maxWidth: 150 });
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(`Simulation ID: ${result.simulation.id}`, 14, 43);
  doc.text(`Department: ${result.simulation.department}`, 14, 49);

  doc.setFont("helvetica", "bold");
  doc.setFillColor(result.interpretation.classification === "Success" ? 22 : result.interpretation.classification === "Moderate" ? 245 : 220, result.interpretation.classification === "Success" ? 163 : result.interpretation.classification === "Moderate" ? 158 : 38, result.interpretation.classification === "Success" ? 74 : result.interpretation.classification === "Moderate" ? 11 : 38);
  doc.roundedRect(150, 32, 46, 18, 2, 2, "F");
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(13);
  doc.text(result.interpretation.classification.toUpperCase(), 154, 43);

  let y = addSection(doc, "Executive Metrics", 58);
  addKeyValue(doc, "Beneficiary Coverage", formatPercent(result.beneficiary.coverage), 14, y);
  addKeyValue(doc, "Target Fit", `${result.beneficiary.targetFit} / 100`, 77, y);
  addKeyValue(doc, "Equity Score", `${result.equity.overall} / 100`, 140, y);
  y += 28;
  addKeyValue(doc, "Risk Score", `${result.budget.riskScore} / 100`, 14, y);
  addKeyValue(doc, "Fiscal Pressure", formatPercent(result.budget.utilization), 77, y);
  addKeyValue(doc, "Confidence", `${result.simulation.confidenceLevel}%`, 140, y);

  y = addSection(doc, "Population Tested", y + 30);
  addKeyValue(doc, "Base Population", formatCompactNumber(result.beneficiary.basePopulation), 14, y);
  addKeyValue(doc, "Target Group", result.beneficiary.targetUniverse, 77, y, 119);
  y += 27;
  addKeyValue(doc, "Target Population", formatCompactNumber(result.beneficiary.targetPopulation), 14, y);
  addKeyValue(doc, "Beneficiaries", formatCompactNumber(result.beneficiary.beneficiaries), 77, y);
  addKeyValue(doc, "Not Reached", formatCompactNumber(result.beneficiary.nonEligiblePopulation), 140, y);

  y = addSection(doc, "Fiscal Analysis", y + 30);
  addKeyValue(doc, "Planning Envelope", formatCurrency(result.budget.allocatedBudget), 14, y);
  addKeyValue(doc, "Mean Cost", formatCurrency(result.budget.meanCost), 77, y);
  addKeyValue(doc, "Cost / Beneficiary", formatCurrency(result.budget.costPerBeneficiary), 140, y);
  y += 27;
  addKeyValue(doc, "Worst Case Cost", formatCurrency(result.budget.worstCaseCost), 14, y);
  addKeyValue(doc, "Overrun Probability", formatPercent(result.budget.probabilityOverrun), 77, y);
  addKeyValue(doc, "Risk Level", result.budget.riskLevel, 140, y);

  y = addSection(doc, "Interpretation", y + 30);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  const summaryLines = doc.splitTextToSize(result.interpretation.summary, 178);
  doc.text(summaryLines, 16, y);
  y += summaryLines.length * 5 + 6;

  doc.setFont("helvetica", "bold");
  doc.text("Strengths", 16, y);
  y = addList(doc, result.interpretation.strengths, 18, y + 6) + 4;
  doc.setFont("helvetica", "bold");
  doc.text("Concerns", 16, y);
  y = addList(doc, result.interpretation.concerns, 18, y + 6);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(90, 90, 90);
  doc.text("This report is generated from backend simulation output displayed in the PolicySim TN dashboard.", 14, 287);

  const filename = `${result.simulation.id}-${result.simulation.policyName.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}.pdf`;
  doc.save(filename);
}
