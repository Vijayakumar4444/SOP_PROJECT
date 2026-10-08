import { z } from "zod";

export const policyRuleSchema = z.object({
  id: z.string(),
  attribute: z.string().min(1, "Choose an attribute."),
  operator: z.enum(["=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "BETWEEN"]),
  value: z.string().min(1, "Enter a comparison value."),
  joiner: z.enum(["AND", "OR"])
});

export const policySchema = z.object({
  name: z.string().min(4, "Enter a descriptive policy name."),
  department: z.string().min(1, "Choose a department."),
  description: z.string().min(20, "Describe the policy in enough detail for review."),
  objectives: z.string().optional(),
  budgetAllocation: z.number().positive().optional(),
  benefitAmount: z.number().positive().optional(),
  benefitFrequency: z.enum(["Monthly", "Annual", "One-time"]).optional(),
  administrativeCostPercent: z.number().min(0).max(100).optional(),
  benchmarkActualBeneficiaries: z.number().positive().optional(),
  benchmarkActualAnnualCost: z.number().positive().optional(),
  benchmarkDate: z.string().optional(),
  benchmarkSource: z.string().optional(),
  geographicScope: z.string(),
  selectedDistricts: z.array(z.string()),
  rules: z.array(policyRuleSchema).min(1, "Add at least one eligibility rule.")
});
