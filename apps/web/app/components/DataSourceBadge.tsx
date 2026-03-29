import type { DataSourceMode } from "@/lib/api";

export function DataSourceBadge({ sourceMode }: { sourceMode: DataSourceMode }) {
  return <span className="pill">{sourceMode === "live" ? "API live" : "Demo mode"}</span>;
}
