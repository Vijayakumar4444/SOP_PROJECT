import {
  Activity,
  BarChart3,
  BookOpenCheck,
  Database,
  FileBarChart,
  FileText,
  GitCompare,
  Home,
  Info,
  Map,
  PlusCircle,
  Settings
} from "lucide-react";
import type { Department, PolicyRule } from "../types";

export const departments: Department[] = [
  "Social Welfare",
  "Rural Development",
  "Education",
  "Health",
  "Agriculture",
  "Labour",
  "Housing",
  "Other"
];

export const tamilNaduDistricts = [
  "Ariyalur",
  "Chengalpattu",
  "Chennai",
  "Coimbatore",
  "Cuddalore",
  "Dharmapuri",
  "Dindigul",
  "Erode",
  "Kallakurichi",
  "Kancheepuram",
  "Karur",
  "Krishnagiri",
  "Madurai",
  "Mayiladuthurai",
  "Nagapattinam",
  "Namakkal",
  "Nilgiris",
  "Perambalur",
  "Pudukkottai",
  "Ramanathapuram",
  "Ranipet",
  "Salem",
  "Sivaganga",
  "Tenkasi",
  "Thanjavur",
  "Theni",
  "Thoothukudi",
  "Tiruchirappalli",
  "Tirunelveli",
  "Tirupathur",
  "Tiruppur",
  "Tiruvallur",
  "Tiruvannamalai",
  "Tiruvarur",
  "Vellore",
  "Viluppuram",
  "Virudhunagar"
];

export const ruleAttributes = [
  "Gender",
  "Age",
  "Annual Income",
  "Household Income",
  "District",
  "Urban/Rural",
  "Social Group",
  "Occupation",
  "Employment Status",
  "Education",
  "Household Size",
  "Disability Status",
  "Land Ownership",
  "Existing Scheme Beneficiary",
  "Residence"
];

export const defaultRules: PolicyRule[] = [
  { id: "rule-1", attribute: "Gender", operator: "=", value: "Female", joiner: "AND" },
  { id: "rule-2", attribute: "Age", operator: ">=", value: "21", joiner: "AND" },
  { id: "rule-3", attribute: "Age", operator: "<=", value: "60", joiner: "AND" },
  { id: "rule-4", attribute: "Household Income", operator: "<", value: "250000", joiner: "AND" },
  { id: "rule-5", attribute: "Residence", operator: "=", value: "Tamil Nadu", joiner: "AND" }
];

export const navItems = [
  { label: "Overview", href: "/", icon: Home },
  { label: "New Simulation", href: "/new-simulation", icon: PlusCircle },
  { label: "Simulation History", href: "/simulations", icon: BookOpenCheck },
  { label: "Comparative Analysis", href: "/compare", icon: GitCompare },
  { label: "District Analytics", href: "/districts", icon: Map },
  { label: "Reports", href: "/reports", icon: FileText },
  { label: "Power BI", href: "/power-bi", icon: FileBarChart },
  { label: "System Information", href: "/system", icon: Info }
];

export const overviewWorkflow = [
  { label: "Define Policy", icon: FileText },
  { label: "Verify Rules", icon: Settings },
  { label: "Run Monte Carlo", icon: Activity },
  { label: "Analyze Results", icon: BarChart3 },
  { label: "Publish Reports", icon: Database }
];
