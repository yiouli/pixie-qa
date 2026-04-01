/** Datasets panel — sidebar list + table viewer */

import { useState, useEffect } from "react";
import type { ArtifactEntry, DatasetData } from "../types";
import { SidebarList } from "./SidebarList";

interface DatasetsPanelProps {
  datasets: ArtifactEntry[];
  autoSelect?: string | null;
}

export function DatasetsPanel({ datasets, autoSelect }: DatasetsPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    datasets[0]?.path ?? null,
  );
  const [data, setData] = useState<DatasetData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (autoSelect) {
      setSelected(autoSelect);
    }
  }, [autoSelect]);

  useEffect(() => {
    if (
      selected &&
      !datasets.some((d) => d.path === selected) &&
      datasets.length > 0
    ) {
      setSelected(datasets[0].path);
    }
  }, [datasets, selected]);

  useEffect(() => {
    if (!selected) {
      setData(null);
      return;
    }
    setLoading(true);
    fetch(`/api/file?path=${encodeURIComponent(selected)}`)
      .then((r) => r.json())
      .then((d: DatasetData) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selected]);

  return (
    <div className="split-panel">
      <aside className="split-sidebar">
        <SidebarList
          items={datasets}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No datasets yet"
        />
      </aside>
      <div className="split-main">
        {loading ? (
          <div className="empty-state">Loading…</div>
        ) : data ? (
          <DatasetTable data={data} />
        ) : (
          <div className="empty-state">
            <p>Select a dataset to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

function DatasetTable({ data }: { data: DatasetData }) {
  if (!data.items || data.items.length === 0) {
    return <div className="empty-state">Dataset is empty</div>;
  }

  // Derive columns from keys of first item
  const allKeys = new Set<string>();
  for (const item of data.items) {
    for (const key of Object.keys(item)) {
      allKeys.add(key);
    }
  }
  const columns = Array.from(allKeys);

  return (
    <div className="dataset-table-wrap">
      <div className="dataset-header">
        <span className="dataset-name">{data.name}</span>
        <span className="dataset-count">{data.items.length} items</span>
      </div>
      <div className="table-scroll">
        <table className="dataset-table">
          <thead>
            <tr>
              <th>#</th>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((item, idx) => (
              <tr key={idx}>
                <td className="row-num">{idx + 1}</td>
                {columns.map((col) => (
                  <td key={col}>
                    <CellValue value={item[col]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CellValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="cell-null">—</span>;
  }
  if (typeof value === "string") {
    const truncated = value.length > 200 ? value.slice(0, 200) + "…" : value;
    return <span className="cell-text">{truncated}</span>;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return <span className="cell-primitive">{String(value)}</span>;
  }
  // Object / array: render as compact JSON
  const json = JSON.stringify(value, null, 1);
  const truncated = json.length > 300 ? json.slice(0, 300) + "…" : json;
  return <pre className="cell-json">{truncated}</pre>;
}
