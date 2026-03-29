interface StatusBadgeProps {
  status: "passed" | "failed" | "error";
}

const labels: Record<string, string> = {
  passed: "PASS",
  failed: "FAIL",
  error: "ERROR",
};

const classes: Record<string, string> = {
  passed: "pass",
  failed: "fail",
  error: "error",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`badge ${classes[status]}`}>{labels[status]}</span>;
}
