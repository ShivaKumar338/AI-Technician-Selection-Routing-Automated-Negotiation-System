export const STATUS_STYLES = {
  pending:     "bg-slate-500/20 text-slate-300",
  matched:     "bg-secondary/20 text-secondary",
  negotiating: "bg-amber-500/20 text-amber-300",
  assigned:    "bg-primary/20 text-primary",
  completed:   "bg-emerald-500/20 text-emerald-300",
  rejected:    "bg-red-500/20 text-red-300",
  timeout:     "bg-slate-600/20 text-slate-400",
};

export const STATUS_LABELS = {
  pending:     "Pending",
  matched:     "Matched",
  negotiating: "Negotiating",
  assigned:    "Assigned",
  completed:   "Completed",
  rejected:    "Rejected",
  timeout:     "Timed Out",
};

export function getStatusStyle(status) {
  return STATUS_STYLES[status] || STATUS_STYLES.pending;
}

export function getStatusLabel(status) {
  return STATUS_LABELS[status] || status;
}
