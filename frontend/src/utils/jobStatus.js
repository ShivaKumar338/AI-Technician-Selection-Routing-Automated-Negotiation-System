export const STATUS_STYLES = {
  pending: "bg-slate-500/20 text-slate-300",
  matched: "bg-secondary/20 text-secondary",
  negotiating: "bg-amber-500/20 text-amber-300",
  assigned: "bg-primary/20 text-primary",
  completed: "bg-emerald-500/20 text-emerald-300",
};

export function getStatusStyle(status) {
  return STATUS_STYLES[status] || STATUS_STYLES.pending;
}
