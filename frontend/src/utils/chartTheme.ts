import type { EChartsOption } from "echarts";

export const chartColors = ["#15803D", "#16A34A", "#86EFAC", "#2563EB", "#F59E0B", "#DC2626", "#6B7280"];

export const baseChartOptions: EChartsOption = {
  color: chartColors,
  textStyle: {
    fontFamily: "Poppins, system-ui, sans-serif",
    color: "#111111"
  },
  grid: {
    left: 44,
    right: 24,
    top: 32,
    bottom: 36,
    containLabel: true
  },
  tooltip: {
    trigger: "axis",
    backgroundColor: "#ffffff",
    borderColor: "#D1D5DB",
    borderWidth: 1,
    textStyle: { color: "#111111" },
    extraCssText: "box-shadow: 0 6px 18px rgba(17,17,17,0.08); border-radius: 8px;"
  }
};

export function mergeChartOptions(option: EChartsOption): EChartsOption {
  return {
    ...baseChartOptions,
    ...option,
    grid: { ...(baseChartOptions.grid as object), ...(option.grid as object) }
  };
}
