import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { Download, Maximize2 } from "lucide-react";
import { mergeChartOptions } from "../../utils/chartTheme";

interface EChartsPanelProps {
  option: EChartsOption;
  height?: number;
  ariaLabel: string;
}

export function EChartsPanel({ option, height = 320, ariaLabel }: EChartsPanelProps) {
  return (
    <div className="relative" role="img" aria-label={ariaLabel}>
      <div className="absolute right-1 top-1 z-10 flex gap-1">
        <button className="focus-ring rounded-md border border-border bg-white p-1.5 text-muted hover:text-ink" aria-label="Export chart">
          <Download className="h-4 w-4" />
        </button>
        <button className="focus-ring rounded-md border border-border bg-white p-1.5 text-muted hover:text-ink" aria-label="Fullscreen chart">
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
      <ReactECharts option={mergeChartOptions(option)} style={{ height, width: "100%" }} notMerge lazyUpdate />
    </div>
  );
}
