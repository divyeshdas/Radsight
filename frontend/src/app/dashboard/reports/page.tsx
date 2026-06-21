"use client";

import { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import { formatDateTime, severityColor } from "@/lib/utils";
import { Search, Filter, ChevronLeft, ChevronRight, AlertTriangle, Flag, RefreshCw } from "lucide-react";
import type { SeverityLevel } from "@/types";

const SEVERITY_OPTIONS = ["", "normal", "low", "moderate", "high", "critical"];
const STATUS_OPTIONS = ["", "pending", "processing", "completed", "failed"];

interface ReportRow {
  id: string;
  patient_id: string;
  report_type: string;
  status: string;
  severity?: SeverityLevel;
  risk_score?: number;
  classification_confidence?: number;
  findings_count: number;
  has_critical_findings: boolean;
  flagged_for_review: boolean;
  created_at?: string;
  updated_at?: string;
  processing_time_ms?: number;
}

interface PageData {
  items: ReportRow[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export default function ReportsPage() {
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [patient, setPatient] = useState("");
  const [flagged, setFlagged] = useState(false);

  const [data, setData] = useState<PageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dbCount, setDbCount] = useState<number | null>(null);

  // Read initial patient_id from URL without useSearchParams (avoids Next.js 14 Suspense requirement)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pid = params.get("patient_id");
    if (pid) setPatient(pid);
  }, []);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (severity) params.set("severity", severity);
      if (status) params.set("status", status);
      if (patient.trim()) params.set("patient_id", patient.trim());
      if (flagged) params.set("flagged", "true");

      const res = await api.get(`/reports/?${params}`);
      setData(res.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? (err as Error)?.message
        ?? "Failed to load reports";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, severity, status, patient, flagged]);

  // Fetch total DB count separately (no filters) so we always know if there's data
  useEffect(() => {
    api.get("/reports/count")
      .then((r) => setDbCount(r.data.count))
      .catch(() => setDbCount(null));
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const resetFilters = () => {
    setSeverity("");
    setStatus("");
    setPatient("");
    setFlagged(false);
    setPage(1);
  };

  return (
    <div className="flex flex-col flex-1">
      <Navbar title="Reports" subtitle="Manage and review radiology reports" />

      <div className="flex-1 p-6 space-y-4">
        {/* Toolbar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex-1 min-w-48">
            <Input
              placeholder="Search by patient ID..."
              icon={<Search size={13} />}
              value={patient}
              onChange={(e) => { setPatient(e.target.value); setPage(1); }}
            />
          </div>

          <select
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
            className="rounded-lg px-3 py-2 text-sm focus:outline-none"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
          >
            <option value="">All severities</option>
            {SEVERITY_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="rounded-lg px-3 py-2 text-sm focus:outline-none"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>

          <Button
            variant={flagged ? "primary" : "secondary"}
            size="sm"
            onClick={() => { setFlagged(!flagged); setPage(1); }}
          >
            <Filter size={13} />
            Flagged only
          </Button>

          <Button variant="secondary" size="sm" onClick={fetchReports} disabled={loading}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>

        {/* DB diagnostic */}
        {dbCount !== null && (
          <p className="text-xs text-text-muted">
            {dbCount === 0
              ? "No reports in database yet — upload a scan to get started."
              : `${dbCount} report${dbCount !== 1 ? "s" : ""} in database`}
          </p>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg p-3" style={{ background: "#EF444410", border: "1px solid #EF444430" }}>
            <AlertTriangle size={14} style={{ color: "#EF4444" }} />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Table */}
        <div className="panel rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  {["Patient", "Type", "Severity", "Risk", "Confidence", "Date", "Status", ""].map((col) => (
                    <th key={col} className="px-4 py-3 text-left text-xs font-medium text-text-muted whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: "var(--border-subtle)" }}>
                {loading && Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((__, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 rounded bg-surface animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))}

                {!loading && (data?.items ?? []).map((r) => (
                  <tr key={r.id} className="transition-colors">
                    <td className="px-4 py-3 font-medium text-text-primary">{r.patient_id}</td>
                    <td className="px-4 py-3 text-text-secondary capitalize">{(r.report_type || "").replace(/_/g, " ")}</td>
                    <td className="px-4 py-3">
                      {r.severity
                        ? <Badge variant="severity" severity={r.severity} label={r.severity.charAt(0).toUpperCase() + r.severity.slice(1)} />
                        : <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {r.risk_score != null
                        ? (
                          <div className="flex items-center gap-2">
                            <div className="w-14 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-surface)" }}>
                              <div className="h-full rounded-full" style={{ width: `${r.risk_score * 100}%`, backgroundColor: severityColor(r.severity) }} />
                            </div>
                            <span className="text-text-secondary">{(r.risk_score * 100).toFixed(0)}%</span>
                          </div>
                        )
                        : <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {r.classification_confidence != null ? `${Math.round(r.classification_confidence * 100)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-text-muted whitespace-nowrap">
                      {r.created_at ? formatDateTime(r.created_at) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Badge label={r.status || "unknown"} />
                        {r.flagged_for_review && <Flag size={10} className="text-amber-400" />}
                      </div>
                    </td>
                    <td className="px-4 py-3" />
                  </tr>
                ))}
              </tbody>
            </table>

            {!loading && !error && (data?.items ?? []).length === 0 && (
              <div className="py-12 text-center space-y-2">
                <p className="text-text-muted text-xs">No reports match your filters.</p>
                {(patient || severity || status || flagged) && (
                  <button onClick={resetFilters} className="text-xs text-accent-blue hover:underline">
                    Clear filters
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Pagination + count */}
        {data && !error && (
          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>
              {data.total === 0 ? "No results" : `${data.total.toLocaleString()} result${data.total !== 1 ? "s" : ""}`}
              {(patient || severity || status) ? " (filtered)" : ""}
            </span>
            {data.pages > 1 && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  <ChevronLeft size={13} />
                </Button>
                <span>Page {page} of {data.pages}</span>
                <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>
                  <ChevronRight size={13} />
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
