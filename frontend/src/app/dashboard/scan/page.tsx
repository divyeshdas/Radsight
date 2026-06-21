"use client";

import { useState, useRef, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import { severityColor, formatMs } from "@/lib/utils";
import {
  Upload, FileText, AlertTriangle, CheckCircle2,
  ClipboardList, Clock, Zap, X, FileScan, FileSearch, Inbox, Sparkles,
} from "lucide-react";
import type { SeverityLevel } from "@/types";

const REPORT_TYPES = [
  { value: "chest_xray", label: "Chest X-Ray" },
  { value: "ct_scan",    label: "CT Scan" },
  { value: "mri",        label: "MRI" },
  { value: "ultrasound", label: "Ultrasound" },
  { value: "mammogram",  label: "Mammogram" },
  { value: "other",      label: "Other" },
];

const ACCEPTED = ".pdf,.txt,.png,.jpg,.jpeg,.tiff";

interface ScanResult {
  id: string;
  patient_id: string;
  report_type: string;
  severity?: SeverityLevel;
  risk_score?: number;
  classification_confidence?: number;
  ai_summary?: string;
  findings_count: number;
  has_critical_findings: boolean;
  flagged_for_review: boolean;
  processing_time_ms?: number;
  tags: string[];
  status: string;
}

function RiskMeter({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.75 ? "#EF4444" : score >= 0.5 ? "#F97316" : score >= 0.25 ? "#F59E0B" : "#10B981";
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-text-muted">Risk Score</span>
        <span className="text-base font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "var(--bg-surface)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function ResultPanel({ result }: { result: ScanResult }) {
  const sev = result.severity ?? "normal";
  const isCritical = result.has_critical_findings;
  const tags = result.tags.filter((t) => !["normal", "low", "moderate", "high", "critical"].includes(t));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            {isCritical ? (
              <AlertTriangle size={18} className="text-red-500" />
            ) : (
              <CheckCircle2 size={18} className="text-emerald-500" />
            )}
            <span className="text-base font-semibold text-text-primary">
              {isCritical ? "Critical Findings Detected" : "Analysis Complete"}
            </span>
          </div>
          <p className="text-sm text-text-muted font-semibold">Patient: {result.patient_id}</p>
        </div>
        <Badge
          variant="severity"
          severity={sev as SeverityLevel}
          label={sev.charAt(0).toUpperCase() + sev.slice(1)}
        />
      </div>

      {/* Risk meter */}
      {result.risk_score != null && <RiskMeter score={result.risk_score} />}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          {
            icon: Brain,
            label: "Confidence",
            value: result.classification_confidence != null
              ? `${(result.classification_confidence * 100).toFixed(1)}%`
              : "—",
            color: "#8B5CF6",
          },
          {
            icon: Zap,
            label: "Findings",
            value: String(result.findings_count),
            color: severityColor(sev),
          },
          {
            icon: Clock,
            label: "Process time",
            value: result.processing_time_ms != null ? formatMs(result.processing_time_ms) : "—",
            color: "#06B6D4",
          },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="rounded-lg p-4 text-center" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
            <Icon size={16} style={{ color }} className="mx-auto mb-1.5" />
            <p className="text-base font-bold" style={{ color }}>{value}</p>
            <p className="text-xs text-text-muted mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* AI Summary */}
      {result.ai_summary && (
        <div className="rounded-lg p-4" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <p className="text-xs font-medium text-text-muted mb-2">AI Assessment</p>
          <p className="text-sm text-text-secondary leading-relaxed">{result.ai_summary}</p>
        </div>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-text-muted">Detected Conditions</p>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xs px-3 py-1 rounded-full font-medium"
                style={{ background: `${severityColor(sev)}18`, color: severityColor(sev), border: `1px solid ${severityColor(sev)}30` }}
              >
                {tag.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.flagged_for_review && (
        <div className="flex items-center gap-2 rounded-lg p-3.5" style={{ background: "#F9731610", border: "1px solid #F9731630" }}>
          <AlertTriangle size={15} style={{ color: "#F97316" }} />
          <p className="text-sm font-medium" style={{ color: "#F97316" }}>Flagged for radiologist review</p>
        </div>
      )}
    </div>
  );
}

export default function ScanPage() {
  const [file, setFile] = useState<File | null>(null);
  const [patientId, setPatientId] = useState("");
  const [reportType, setReportType] = useState("chest_xray");
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) { setFile(f); setResult(null); setError(null); }
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setFile(f); setResult(null); setError(null); }
  };

  const handleSubmit = async () => {
    if (!file || !patientId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("patient_id", patientId.trim());
      form.append("report_type", reportType);

      const res = await api.post("/reports/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const data = res.data;
      setResult({
        id: data.id ?? data._id ?? "",
        patient_id: data.patient_id,
        report_type: data.report_type,
        severity: data.severity,
        risk_score: data.risk_score,
        classification_confidence: data.classification_confidence,
        ai_summary: data.ai_summary,
        findings_count: data.findings_count ?? 0,
        has_critical_findings: data.has_critical_findings ?? false,
        flagged_for_review: data.flagged_for_review ?? false,
        processing_time_ms: data.processing_time_ms,
        tags: data.tags ?? [],
        status: data.status,
      });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="flex flex-col flex-1">
      <Navbar title="Upload Scan" subtitle="Upload a radiology report for AI analysis" />

      <div className="flex-1 p-6 flex flex-col">
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Upload form */}
          <div className="flex flex-col gap-4">
            <Card glass className="flex-1 flex flex-col">
              <div className="flex items-center gap-2 mb-5">
                <FileScan size={16} className="text-accent-blue" />
                <span className="text-base font-semibold text-text-primary">Report File</span>
              </div>

              {/* Drop zone */}
              <div
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className="relative rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200 flex flex-col items-center justify-center gap-4 flex-1 min-h-[200px]"
                style={{
                  borderColor: dragging ? "var(--accent-blue)" : file ? "#10B981" : "var(--border-color)",
                  background: dragging ? "var(--accent-blue)08" : file ? "#10B98108" : "var(--bg-surface)",
                }}
              >
                <input ref={inputRef} type="file" accept={ACCEPTED} onChange={onFileChange} className="hidden" />

                {file ? (
                  <>
                    <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: "#10B98115" }}>
                      <FileText size={26} style={{ color: "#10B981" }} />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-text-primary">{file.name}</p>
                      <p className="text-xs text-text-muted mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); reset(); }}
                      className="absolute top-3 right-3 p-1.5 rounded-full hover:bg-surface transition-colors"
                    >
                      <X size={14} className="text-text-muted" />
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
                      <Upload size={26} className="text-text-muted" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-text-primary">Drop file here or click to browse</p>
                      <p className="text-xs text-text-muted mt-1.5">PDF, TXT, PNG, JPG, TIFF · Max 50MB</p>
                    </div>
                  </>
                )}
              </div>
            </Card>

            <Card glass>
              <div className="flex items-center gap-2 mb-5">
                <ClipboardList size={16} className="text-accent-blue" />
                <span className="text-base font-semibold text-text-primary">Patient Details</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">Patient ID</label>
                  <Input
                    placeholder="e.g. PAT00042"
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">Scan Type</label>
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary focus:outline-none focus:border-accent-blue/60"
                    style={{ background: "var(--bg-surface)", borderColor: "var(--border-color)", color: "var(--text-primary)" }}
                  >
                    {REPORT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {error && (
                <div className="mt-4 flex items-center gap-2 rounded-lg p-3" style={{ background: "#EF444410", border: "1px solid #EF444430" }}>
                  <AlertTriangle size={14} style={{ color: "#EF4444" }} />
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              <Button
                className="w-full mt-5"
                onClick={handleSubmit}
                loading={loading}
                disabled={!file || !patientId.trim()}
              >
                <Sparkles size={15} />
                {loading ? "Analyzing…" : "Run AI Analysis"}
              </Button>
            </Card>
          </div>

          {/* Results */}
          <div className="flex flex-col">
            <Card glass className="flex-1">
              <div className="flex items-center gap-2 mb-5">
                <FileSearch size={16} className="text-accent-blue" />
                <span className="text-base font-semibold text-text-primary">Analysis Results</span>
              </div>

              {result ? (
                <ResultPanel result={result} />
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center pb-10">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
                    <Inbox size={28} className="text-text-muted" />
                  </div>
                  <div>
                    <p className="text-base font-medium text-text-primary">No results yet</p>
                    <p className="text-sm text-text-muted mt-1.5">
                      Upload a scan and click<br />Run AI Analysis to see results
                    </p>
                  </div>
                </div>
              )}
            </Card>
          </div>

        </div>
      </div>
    </div>
  );
}
