import React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={cn("animate-pulse rounded bg-surface", className)} style={style} />
  );
}

export function KPICardSkeleton() {
  return (
    <div className="panel rounded-xl p-5">
      <Skeleton className="h-3 w-24 mb-4" />
      <Skeleton className="h-8 w-32 mb-2" />
      <Skeleton className="h-3 w-20" />
    </div>
  );
}

export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div className="panel rounded-xl p-4">
      <Skeleton className="h-3 w-32 mb-4" />
      <Skeleton className="w-full rounded" style={{ height }} />
    </div>
  );
}
