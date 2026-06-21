"use client";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn, formatDateTime, truncate, severityColor } from "@/lib/utils";
import type { RadiologyReport } from "@/types";
import { ChevronRight, Flag } from "lucide-react";

interface ReportTableProps {
  reports: RadiologyReport[];
  onSelect?: (report: RadiologyReport) => void;
  isLoading?: boolean;
}

const COLS = ["Patient", "Type", "Severity", "Risk", "Confidence", "Date", "Status", ""];

export function ReportTable({ reports, onSelect, isLoading }: ReportTableProps) {
  if (isLoading) {
    return (
      <div className="panel rounded-xl overflow-hidden">
        <div className="p-4 space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-10 rounded bg-surface animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="panel rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              {COLS.map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-medium text-text-muted whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: "var(--border-subtle)" }}>
            {reports.map((r) => (
              <tr key={r.id}
                onClick={() => onSelect?.(r)}
                className={cn(
                  "transition-colors",
                  onSelect && "cursor-pointer hover:bg-surface/60"
                )}>
                <td className="px-4 py-3 font-medium text-text-primary">{r.patient_id}</td>
                <td className="px-4 py-3 text-text-secondary capitalize">{r.report_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3">
                  {r.severity
                    ? <Badge variant="severity" severity={r.severity} label={r.severity.charAt(0).toUpperCase() + r.severity.slice(1)} />
                    : <span className="text-text-muted">—</span>}
                </td>
                <td className="px-4 py-3">
                  {r.risk_score != null
                    ? <div className="flex items-center gap-2">
                        <div className="w-14 h-1.5 rounded-full bg-surface overflow-hidden">
                          <div className="h-full rounded-full transition-all"
                            style={{ width: `${r.risk_score * 100}%`, backgroundColor: severityColor(r.severity ?? "") }} />
                        </div>
                        <span className="text-text-secondary">{(r.risk_score * 100).toFixed(0)}%</span>
                      </div>
                    : <span className="text-text-muted">—</span>}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {r.classification_confidence != null
                    ? `${Math.round(r.classification_confidence * 100)}%`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-text-muted whitespace-nowrap">{formatDateTime(r.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <Badge label={r.status} />
                    {r.flagged_for_review && <Flag size={10} className="text-amber-400" />}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {onSelect && <ChevronRight size={13} className="text-text-muted" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {reports.length === 0 && (
          <div className="py-12 text-center text-text-muted text-xs">No reports found</div>
        )}
      </div>
    </div>
  );
}
