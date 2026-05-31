"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Navbar } from "@/components/layout/Navbar";
import { ReportTable } from "@/components/reports/ReportTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { Search, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import type { RadiologyReport, PaginatedResponse } from "@/types";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const SEVERITY_OPTIONS = ["", "normal", "low", "moderate", "high", "critical"];
const STATUS_OPTIONS = ["", "pending", "processing", "completed", "failed"];

export default function ReportsPage() {
  const searchParams = useSearchParams();
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [patient, setPatient] = useState(searchParams.get("patient_id") ?? "");
  const [flagged, setFlagged] = useState(false);

  useEffect(() => {
    const pid = searchParams.get("patient_id");
    if (pid) setPatient(pid);
  }, [searchParams]);

  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  if (severity) params.set("severity", severity);
  if (status) params.set("status", status);
  if (patient) params.set("patient_id", patient);
  if (flagged) params.set("flagged", "true");

  const { data, isLoading } = useSWR<PaginatedResponse<RadiologyReport>>(
    `/reports/?${params}`, fetcher, { keepPreviousData: true }
  );

  const handleFilterChange = () => setPage(1);

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
              onChange={(e) => { setPatient(e.target.value); handleFilterChange(); }}
            />
          </div>

          <select
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); handleFilterChange(); }}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue/60">
            <option value="">All severities</option>
            {SEVERITY_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); handleFilterChange(); }}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue/60">
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>

          <Button
            variant={flagged ? "primary" : "secondary"}
            size="sm"
            onClick={() => { setFlagged(!flagged); handleFilterChange(); }}>
            <Filter size={13} />
            Flagged only
          </Button>
        </div>

        {/* Table */}
        <ReportTable reports={data?.items ?? []} isLoading={isLoading} />

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>{data.total.toLocaleString()} total reports</span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={13} />
              </Button>
              <span className="font-mono">Page {page} of {data.pages}</span>
              <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>
                <ChevronRight size={13} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
