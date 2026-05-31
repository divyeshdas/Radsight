"use client";

import { useState } from "react";
import useSWR from "swr";
import ReactECharts from "echarts-for-react";
import { Navbar } from "@/components/layout/Navbar";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ChartSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/utils";
import {
  TrendingUp, TrendingDown, Minus,
  AlertTriangle, Cpu, Activity, Zap,
} from "lucide-react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const PERIOD_OPTIONS = [
  { label: "30d",  value: 30  },
  { label: "60d",  value: 60  },
  { label: "90d",  value: 90  },
  { label: "180d", value: 180 },
];

const CHART_TEXT  = "var(--text-secondary)";
const CHART_MUTED = "var(--text-muted)";
const GRID_COLOR  = "var(--border-color)";
const TOOLTIP_BG  = "var(--bg-elevated)";
const TOOLTIP_BORDER = "var(--border-color)";

function tooltipStyle() {
  return {
    backgroundColor: TOOLTIP_BG,
    borderColor: TOOLTIP_BORDER,
    borderWidth: 1,
    textStyle: { color: CHART_TEXT, fontSize: 11 },
  };
}

// ---------- sub-charts ----------

function VolumeChart({ data }: { data: { date: string; count: number; sma7: number }[] }) {
  const option = {
    backgroundColor: "transparent",
    tooltip: { ...tooltipStyle(), trigger: "axis", axisPointer: { type: "cross", crossStyle: { color: CHART_MUTED } } },
    legend: {
      data: ["Volume", "7-day MA"],
      textStyle: { color: CHART_MUTED, fontSize: 11 },
      top: 4, right: 4,
    },
    grid: { top: 36, right: 16, bottom: 40, left: 48, containLabel: false },
    xAxis: {
      type: "category",
      data: data.map((d) => d.date),
      axisLabel: {
        color: CHART_MUTED, fontSize: 10,
        formatter: (v: string) => {
          const d = new Date(v);
          return `${d.getMonth() + 1}/${d.getDate()}`;
        },
        interval: Math.floor(data.length / 8),
      },
      axisLine: { lineStyle: { color: GRID_COLOR } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: CHART_MUTED, fontSize: 10 },
      splitLine: { lineStyle: { color: GRID_COLOR, type: "dashed" } },
    },
    series: [
      {
        name: "Volume",
        type: "bar",
        data: data.map((d) => d.count),
        itemStyle: { color: "#0EA5E9", borderRadius: [2, 2, 0, 0], opacity: 0.7 },
        barMaxWidth: 12,
      },
      {
        name: "7-day MA",
        type: "line",
        data: data.map((d) => d.sma7),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#10B981", width: 2 },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 240 }} />;
}

function ForecastDeepChart({
  data,
}: {
  data: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number; trend: number }[];
}) {
  const option = {
    backgroundColor: "transparent",
    tooltip: {
      ...tooltipStyle(), trigger: "axis",
      formatter: (params: { seriesName: string; value: number; axisValueLabel: string }[]) => {
        const date = params[0]?.axisValueLabel ?? "";
        const lines = params
          .filter((p) => p.seriesName !== "CI_lower")
          .map((p) => {
            const label = p.seriesName === "CI_band" ? "CI upper" : p.seriesName;
            return `<div style="display:flex;gap:12px;justify-content:space-between"><span>${label}</span><b>${Math.round(p.value)}</b></div>`;
          })
          .join("");
        return `<div style="font-size:10px;line-height:1.7"><div style="margin-bottom:4px;font-weight:600">${date}</div>${lines}</div>`;
      },
    },
    legend: {
      data: ["Forecast", "Trend", "CI band"],
      textStyle: { color: CHART_MUTED, fontSize: 11 },
      top: 4, right: 4,
    },
    grid: { top: 36, right: 16, bottom: 40, left: 52, containLabel: false },
    xAxis: {
      type: "category",
      data: data.map((d) => d.ds),
      axisLabel: {
        color: CHART_MUTED, fontSize: 10,
        formatter: (v: string) => {
          const d = new Date(v);
          return `${d.getMonth() + 1}/${d.getDate()}`;
        },
        interval: Math.floor(data.length / 6),
      },
      axisLine: { lineStyle: { color: GRID_COLOR } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: CHART_MUTED, fontSize: 10 },
      splitLine: { lineStyle: { color: GRID_COLOR, type: "dashed" } },
    },
    series: [
      {
        name: "CI_lower",
        type: "line",
        data: data.map((d) => d.yhat_lower),
        lineStyle: { opacity: 0 },
        symbol: "none",
        stack: "ci",
        areaStyle: { opacity: 0 },
      },
      {
        name: "CI band",
        type: "line",
        data: data.map((d) => d.yhat_upper - d.yhat_lower),
        lineStyle: { opacity: 0 },
        symbol: "none",
        stack: "ci",
        areaStyle: { color: "#0EA5E9", opacity: 0.12 },
        tooltip: { show: false },
      },
      {
        name: "Forecast",
        type: "line",
        data: data.map((d) => d.yhat),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#0EA5E9", width: 2 },
        itemStyle: { color: "#0EA5E9" },
      },
      {
        name: "Trend",
        type: "line",
        data: data.map((d) => d.trend),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#8B5CF6", width: 1.5, type: "dashed" },
        itemStyle: { color: "#8B5CF6" },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 240 }} />;
}

function DiseasePrevalenceChart({ data }: { data: { disease: string; total: number; critical: number; avg_risk: number }[] }) {
  const sorted = [...data].sort((a, b) => b.total - a.total).slice(0, 10);
  const option = {
    backgroundColor: "transparent",
    tooltip: {
      ...tooltipStyle(), trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    legend: {
      data: ["Total", "Critical"],
      textStyle: { color: CHART_MUTED, fontSize: 11 },
      top: 4, right: 4,
    },
    grid: { top: 36, right: 16, bottom: 16, left: 16, containLabel: true },
    xAxis: { type: "value", axisLabel: { color: CHART_MUTED, fontSize: 10 }, splitLine: { lineStyle: { color: GRID_COLOR, type: "dashed" } } },
    yAxis: {
      type: "category",
      data: sorted.map((d) => d.disease),
      axisLabel: {
        color: CHART_TEXT, fontSize: 11,
        formatter: (v: string) => v.length > 18 ? v.slice(0, 16) + "…" : v,
      },
      axisLine: { lineStyle: { color: GRID_COLOR } },
    },
    series: [
      {
        name: "Total",
        type: "bar",
        data: sorted.map((d) => d.total),
        itemStyle: { color: "#0EA5E9", borderRadius: [0, 3, 3, 0], opacity: 0.85 },
        barMaxWidth: 16,
      },
      {
        name: "Critical",
        type: "bar",
        data: sorted.map((d) => d.critical),
        itemStyle: { color: "#EF4444", borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 16,
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 300 }} />;
}

function ConfidenceHistogram({ data }: { data: { bucket: string; count: number }[] }) {
  const option = {
    backgroundColor: "transparent",
    tooltip: { ...tooltipStyle(), trigger: "axis" },
    grid: { top: 20, right: 16, bottom: 40, left: 48 },
    xAxis: {
      type: "category",
      data: data.map((d) => d.bucket),
      axisLabel: { color: CHART_MUTED, fontSize: 10 },
      axisLine: { lineStyle: { color: GRID_COLOR } },
    },
    yAxis: {
      type: "value",
      name: "Reports",
      nameTextStyle: { color: CHART_MUTED, fontSize: 10 },
      axisLabel: { color: CHART_MUTED, fontSize: 10 },
      splitLine: { lineStyle: { color: GRID_COLOR, type: "dashed" } },
    },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.count),
        itemStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "#8B5CF6" },
              { offset: 1, color: "#8B5CF640" },
            ],
          },
          borderRadius: [3, 3, 0, 0],
        },
        barMaxWidth: 32,
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 200 }} />;
}

function ProcessingLatencyChart({ data }: { data: { date: string; avg_ms: number; p95_ms: number }[] }) {
  const option = {
    backgroundColor: "transparent",
    tooltip: { ...tooltipStyle(), trigger: "axis" },
    legend: {
      data: ["Avg (ms)", "P95 (ms)"],
      textStyle: { color: CHART_MUTED, fontSize: 11 },
      top: 4, right: 4,
    },
    grid: { top: 36, right: 16, bottom: 40, left: 56 },
    xAxis: {
      type: "category",
      data: data.map((d) => d.date),
      axisLabel: {
        color: CHART_MUTED, fontSize: 10,
        formatter: (v: string) => {
          const d = new Date(v);
          return `${d.getMonth() + 1}/${d.getDate()}`;
        },
        interval: Math.floor(data.length / 6),
      },
      axisLine: { lineStyle: { color: GRID_COLOR } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "ms",
      nameTextStyle: { color: CHART_MUTED, fontSize: 10 },
      axisLabel: { color: CHART_MUTED, fontSize: 10 },
      splitLine: { lineStyle: { color: GRID_COLOR, type: "dashed" } },
    },
    series: [
      {
        name: "Avg (ms)",
        type: "line",
        data: data.map((d) => d.avg_ms),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#10B981", width: 2 },
        areaStyle: { color: "#10B98118" },
      },
      {
        name: "P95 (ms)",
        type: "line",
        data: data.map((d) => d.p95_ms),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#F97316", width: 2, type: "dashed" },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 200 }} />;
}

// ---------- anomaly log row ----------

function AnomalyRow({ a }: { a: {
  id: string; anomaly_type: string; severity: string;
  description: string; detected_at: string; deviation_score: number; is_resolved: boolean;
} }) {
  const sevColor: Record<string, string> = {
    critical: "#EF4444", high: "#F97316", medium: "#F59E0B", low: "#10B981",
  };
  const color = sevColor[a.severity] ?? "#6B7280";
  return (
    <div className="flex items-start gap-3 py-3" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
      <div className="mt-0.5 shrink-0">
        <AlertTriangle size={13} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-text-primary">{a.anomaly_type.replace(/_/g, " ")}</span>
          <Badge variant="severity" severity={a.severity as "normal" | "low" | "moderate" | "high" | "critical"}
            label={a.severity} />
          {a.is_resolved && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              style={{ background: "#10B98118", color: "#10B981" }}>
              resolved
            </span>
          )}
        </div>
        <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">{a.description}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-text-muted font-mono">{formatDateTime(a.detected_at)}</span>
          <span className="text-[10px] text-text-muted font-mono">Δ {a.deviation_score.toFixed(2)}σ</span>
        </div>
      </div>
    </div>
  );
}

// ---------- disease trend card ----------

function DiseaseTrendCard({ d }: {
  d: { disease: string; current: number; previous: number; change_pct: number; trend: string }
}) {
  const up   = d.change_pct > 0;
  const flat = Math.abs(d.change_pct) < 2;
  const TrendIcon = flat ? Minus : up ? TrendingUp : TrendingDown;
  const trendColor = flat ? "var(--text-muted)" : up ? "#EF4444" : "#10B981";

  return (
    <div className="flex items-center justify-between py-2.5 px-1"
      style={{ borderBottom: "1px solid var(--border-subtle)" }}>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-text-primary truncate">{d.disease}</p>
        <p className="text-[10px] text-text-muted mt-0.5 font-mono">{formatNumber(d.current)} reports</p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0" style={{ color: trendColor }}>
        <TrendIcon size={12} />
        <span className="text-xs font-mono font-semibold">
          {flat ? "—" : `${up ? "+" : ""}${d.change_pct.toFixed(1)}%`}
        </span>
      </div>
    </div>
  );
}

// ---------- stat pill ----------

function StatPill({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 rounded-lg" style={{ background: "var(--bg-surface)" }}>
      <span className="text-[10px] text-text-muted">{label}</span>
      <span className="text-sm font-bold font-mono" style={{ color: color ?? "var(--text-primary)" }}>
        {value}
      </span>
    </div>
  );
}

// ---------- page ----------

export default function AnalyticsPage() {
  const [days, setDays] = useState(90);
  const [forecastPeriods] = useState(30);

  const { data: trends, isLoading: trendsLoading } = useSWR(
    `/analytics/trends?days=${days}`, fetcher, { refreshInterval: 120000 }
  );
  const { data: forecast, isLoading: forecastLoading } = useSWR(
    `/analytics/forecast?periods=${forecastPeriods}`, fetcher, { refreshInterval: 300000 }
  );
  const { data: anomalies, isLoading: anomalyLoading } = useSWR(
    "/analytics/anomalies", fetcher, { refreshInterval: 60000 }
  );
  const { data: diseases, isLoading: diseasesLoading } = useSWR(
    `/analytics/diseases?days=${days}`, fetcher, { refreshInterval: 120000 }
  );
  const { data: confidence, isLoading: confLoading } = useSWR(
    `/analytics/confidence?days=${days}`, fetcher, { refreshInterval: 120000 }
  );
  const { data: processing, isLoading: procLoading } = useSWR(
    `/analytics/processing?days=${days}`, fetcher, { refreshInterval: 120000 }
  );

  const trendData: { date: string; count: number; sma7: number }[] = trends?.trend_data ?? [];
  const forecastData: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number; trend: number }[] = forecast?.forecast ?? [];
  const anomalyList = anomalies?.anomalies ?? [];
  const diseaseTrends: { disease: string; current: number; previous: number; change_pct: number; trend: string }[] =
    trends?.disease_trends ?? [];
  const diseaseData: { disease: string; total: number; critical: number; avg_risk: number }[] = diseases ?? [];
  const confData: { bucket: string; count: number }[] = confidence?.distribution ?? [];
  const procData: { date: string; avg_ms: number; p95_ms: number }[] = processing?.latency_by_day ?? [];

  const kpis = processing?.summary;

  return (
    <div className="flex flex-col flex-1">
      <Navbar title="Analytics" subtitle="Report trends, forecasts, and system performance" />

      <div className="flex-1 p-6 space-y-6 max-w-screen-2xl mx-auto w-full">

        {/* Period selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Lookback:</span>
          {PERIOD_OPTIONS.map((opt) => (
            <button key={opt.value}
              onClick={() => setDays(opt.value)}
              className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors"
              style={{
                background: days === opt.value ? "var(--accent-blue)" : "var(--bg-surface)",
                color: days === opt.value ? "#fff" : "var(--text-muted)",
                border: `1px solid ${days === opt.value ? "transparent" : "var(--border-color)"}`,
              }}>
              {opt.label}
            </button>
          ))}
        </div>

        {/* Processing KPI pills */}
        {kpis ? (
          <div className="flex flex-wrap gap-3">
            <StatPill label="Total Processed" value={formatNumber(kpis.total_processed)} color="#0EA5E9" />
            <StatPill label="Success Rate" value={`${kpis.success_rate_pct?.toFixed(1)}%`} color="#10B981" />
            <StatPill label="Avg Latency" value={`${kpis.avg_ms?.toFixed(0)}ms`} />
            <StatPill label="P95 Latency" value={`${kpis.p95_ms?.toFixed(0)}ms`} color="#F97316" />
            <StatPill label="Failures" value={formatNumber(kpis.failure_count)} color="#EF4444" />
          </div>
        ) : (
          <div className="flex gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-28 rounded-lg" />
            ))}
          </div>
        )}

        {/* Volume trend + Forecast */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card glass>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity size={13} className="text-accent-blue" />
                <span className="text-sm font-medium text-text-primary">Report Volume</span>
              </div>
              <span className="text-[10px] text-text-muted font-mono">{days}-day window</span>
            </div>
            {trendsLoading
              ? <Skeleton className="h-[240px] w-full rounded-lg" />
              : trendData.length
                ? <VolumeChart data={trendData} />
                : <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">No trend data</div>
            }
          </Card>

          <Card glass>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp size={13} className="text-accent-violet" />
                <span className="text-sm font-medium text-text-primary">Volume Forecast</span>
              </div>
              <span className="text-[10px] text-text-muted font-mono">+{forecastPeriods} days</span>
            </div>
            {forecastLoading
              ? <Skeleton className="h-[240px] w-full rounded-lg" />
              : forecastData.length
                ? <ForecastDeepChart data={forecastData} />
                : <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">No forecast data</div>
            }
          </Card>
        </div>

        {/* Disease prevalence + disease trends */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <Card glass>
              <div className="flex items-center gap-2 mb-4">
                <Zap size={13} className="text-amber-400" />
                <span className="text-sm font-medium text-text-primary">Disease Prevalence</span>
              </div>
              {diseasesLoading
                ? <Skeleton className="h-[300px] w-full rounded-lg" />
                : diseaseData.length
                  ? <DiseasePrevalenceChart data={diseaseData} />
                  : <div className="h-[300px] flex items-center justify-center text-xs text-text-muted">No disease data</div>
              }
            </Card>
          </div>

          <Card glass>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={13} className="text-emerald-400" />
              <span className="text-sm font-medium text-text-primary">Disease Trends</span>
            </div>
            {trendsLoading
              ? <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-10 rounded" />)}</div>
              : diseaseTrends.length
                ? <div className="overflow-auto max-h-[320px] pr-1">
                    {diseaseTrends.map((d) => <DiseaseTrendCard key={d.disease} d={d} />)}
                  </div>
                : <div className="h-[300px] flex items-center justify-center text-xs text-text-muted">No trend data</div>
            }
          </Card>
        </div>

        {/* Confidence distribution + Processing latency */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card glass>
            <div className="flex items-center gap-2 mb-4">
              <Cpu size={13} className="text-violet-400" />
              <span className="text-sm font-medium text-text-primary">Confidence Distribution</span>
            </div>
            {confLoading
              ? <Skeleton className="h-[200px] w-full rounded-lg" />
              : confData.length
                ? <ConfidenceHistogram data={confData} />
                : <div className="h-[200px] flex items-center justify-center text-xs text-text-muted">No distribution data</div>
            }
          </Card>

          <Card glass>
            <div className="flex items-center gap-2 mb-4">
              <Activity size={13} className="text-sky-400" />
              <span className="text-sm font-medium text-text-primary">Processing Latency</span>
            </div>
            {procLoading
              ? <Skeleton className="h-[200px] w-full rounded-lg" />
              : procData.length
                ? <ProcessingLatencyChart data={procData} />
                : <div className="h-[200px] flex items-center justify-center text-xs text-text-muted">No latency data</div>
            }
          </Card>
        </div>

        {/* Anomaly log */}
        <Card glass>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle size={13} className="text-rose-400" />
              <span className="text-sm font-medium text-text-primary">Anomaly Log</span>
            </div>
            {!anomalyLoading && (
              <span className="text-[10px] text-text-muted font-mono">
                {anomalyList.length} event{anomalyList.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {anomalyLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
            </div>
          ) : anomalyList.length ? (
            <div className="divide-y-0">
              {anomalyList.map((a: Parameters<typeof AnomalyRow>[0]["a"]) => (
                <AnomalyRow key={a.id} a={a} />
              ))}
            </div>
          ) : (
            <div className="py-10 text-center text-xs text-text-muted">
              No anomalies detected in the selected period.
            </div>
          )}
        </Card>

      </div>
    </div>
  );
}
