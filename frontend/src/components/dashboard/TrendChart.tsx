"use client";

import ReactECharts from "echarts-for-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

interface TrendRow {
  date: string;
  total_reports: number;
  ma_total?: number | null;
  critical_count?: number;
}

interface TrendChartProps {
  data: TrendRow[];
  title?: string;
}

export function TrendChart({ data, title = "Daily Report Volume" }: TrendChartProps) {
  const dates = data.map((d) => d.date);
  const totals = data.map((d) => d.total_reports);
  const ma = data.map((d) => d.ma_total ?? null);
  const critical = data.map((d) => d.critical_count ?? 0);

  const option = {
    backgroundColor: "transparent",
    grid: { left: 12, right: 12, top: 12, bottom: 40, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: "var(--bg-elevated)",
      borderColor: "var(--border-color)",
      textStyle: { color: "var(--text-primary)", fontSize: 12 },
      axisPointer: { type: "cross", lineStyle: { color: "var(--border-color)" } },
    },
    legend: {
      bottom: 0,
      textStyle: { color: "var(--text-secondary)", fontSize: 11 },
      itemWidth: 12, itemHeight: 2,
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLine: { lineStyle: { color: "var(--border-color)" } },
      axisTick: { show: false },
      axisLabel: {
        color: "var(--text-muted)", fontSize: 10,
        formatter: (v: string) => v.slice(5),
        interval: Math.floor(dates.length / 8),
      },
    },
    yAxis: [
      {
        type: "value",
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: "var(--border-subtle)", type: "dashed" } },
        axisLabel: { color: "var(--text-muted)", fontSize: 10 },
      },
    ],
    series: [
      {
        name: "Reports",
        type: "line",
        data: totals,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#14B8A6", width: 2 },
        itemStyle: { color: "#14B8A6" },
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "#14B8A630" },
              { offset: 1, color: "#14B8A605" },
            ],
          },
        },
      },
      {
        name: "7-day MA",
        type: "line",
        data: ma,
        smooth: true,
        connectNulls: true,
        lineStyle: { color: "#0F766E", width: 1.5, type: "dashed" },
        symbol: "none",
        itemStyle: { color: "#0F766E" },
      },
      {
        name: "Critical",
        type: "line",
        data: critical,
        smooth: true,
        lineStyle: { color: "#EF4444", width: 1.5, type: "dashed" },
        symbol: "none",
        itemStyle: { color: "#EF4444" },
      },
    ],
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-xs text-text-muted">Last 90 days</span>
      </CardHeader>
      <ReactECharts option={option} style={{ height: 240 }} notMerge />
    </Card>
  );
}
