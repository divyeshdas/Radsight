"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { Search, Zap, Clock, BarChart2, FileText } from "lucide-react";
import { formatDateTime, severityColor, truncate } from "@/lib/utils";
import type { SearchResult } from "@/types";

const EXAMPLE_QUERIES = [
  "Show critical chest abnormalities",
  "Find reports with pleural effusion",
  "Pulmonary edema findings",
  "Pneumothorax cases this month",
];

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [meta, setMeta] = useState<{ inference_ms: number; total: number; cache_hit_rate_pct?: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const runSearch = async (q?: string) => {
    const searchQuery = q ?? query;
    if (!searchQuery.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await api.post("/search/semantic", { query: searchQuery, k: 15 });
      setResults(res.data.results ?? []);
      setMeta({ inference_ms: res.data.inference_ms, total: res.data.total, cache_hit_rate_pct: res.data.cache_hit_rate_pct });
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1">
      <Navbar title="Semantic Search" subtitle="Query reports using natural language" />

      <div className="flex-1 p-8 w-full space-y-8">

        {/* Search box */}
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder='e.g. "critical pulmonary findings with cardiomegaly"'
                icon={<Search size={16} />}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
              />
            </div>
            <Button onClick={() => runSearch()} loading={loading} disabled={!query.trim()}>
              <Zap size={15} />
              Search
            </Button>
          </div>

          <div className="flex gap-3 flex-wrap">
            {EXAMPLE_QUERIES.map((q) => (
              <button key={q} onClick={() => { setQuery(q); runSearch(q); }}
                className="text-sm px-4 py-2 rounded-full border border-border text-text-muted hover:text-text-primary hover:border-accent-blue/40 transition-colors">
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Meta */}
        {meta && (
          <div className="flex items-center gap-6 text-sm text-text-muted">
            <span className="flex items-center gap-1.5"><Clock size={13} />{Math.round(meta.inference_ms)}ms</span>
            <span className="flex items-center gap-1.5"><BarChart2 size={13} />{meta.total} results</span>
            {meta.cache_hit_rate_pct != null && (
              <span>cache hit: {meta.cache_hit_rate_pct}%</span>
            )}
          </div>
        )}

        {/* Results */}
        {loading && (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-32 rounded-xl bg-surface animate-pulse" />
            ))}
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <div className="text-center py-20 text-text-muted text-base">
            No reports matched your query. Try different search terms.
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-4">
            {results.map((r) => (
              <Card key={r.report_id} glass className="hover:border-accent-blue/30 transition-colors">
                <div className="flex items-start justify-between gap-6 py-1">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-medium text-text-primary">{r.patient_id}</span>
                      {r.severity && (
                        <Badge variant="severity" severity={r.severity}
                          label={r.severity.charAt(0).toUpperCase() + r.severity.slice(1)} />
                      )}
                    </div>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {truncate(r.summary ?? "No summary available", 260)}
                    </p>
                    <p className="text-xs text-text-muted mt-3">{formatDateTime(r.created_at)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-3 shrink-0">
                    <div className="text-right">
                      <div className="text-lg font-semibold" style={{ color: severityColor(r.severity) }}>
                        {Math.round(r.score * 100)}%
                      </div>
                      <div className="text-xs text-text-muted">similarity</div>
                    </div>
                    <button
                      onClick={() => router.push(`/dashboard/reports?patient_id=${encodeURIComponent(r.patient_id)}`)}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-text-muted hover:text-accent-blue transition-colors"
                      style={{ border: "1px solid var(--border-subtle)" }}
                    >
                      <FileText size={12} />
                      View in Reports
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
