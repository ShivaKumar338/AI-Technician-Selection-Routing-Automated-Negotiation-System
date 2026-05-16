import { PROBLEM_TYPES } from "../../utils/problemTypes";
import { cn } from "../../utils/cn";

const URGENCY_LABELS = { 1: "Low", 2: "Low-Med", 3: "Medium", 4: "High", 5: "Critical" };

export default function JobForm({ form, onChange, onSubmit, submitting }) {
  return (
    <form onSubmit={onSubmit} className="card-surface space-y-6 p-6">
      <div>
        <label className="mb-3 block text-sm font-medium text-muted">Problem Type</label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {PROBLEM_TYPES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => onChange("problem_type", value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border p-4 transition",
                form.problem_type === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-background text-muted hover:border-primary/40"
              )}
            >
              <Icon className="h-6 w-6" />
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-medium text-muted">Latitude</label>
          <input
            type="number"
            step="any"
            value={form.customer_lat}
            onChange={(e) => onChange("customer_lat", e.target.value)}
            className="w-full rounded-xl border border-border bg-background px-4 py-3 text-foreground outline-none focus:border-primary"
            required
          />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-muted">Longitude</label>
          <input
            type="number"
            step="any"
            value={form.customer_lng}
            onChange={(e) => onChange("customer_lng", e.target.value)}
            className="w-full rounded-xl border border-border bg-background px-4 py-3 text-foreground outline-none focus:border-primary"
            required
          />
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-sm font-medium text-muted">Urgency</label>
          <span className="rounded-lg bg-amber-500/20 px-2 py-1 text-xs font-semibold text-amber-300">
            {form.urgency} - {URGENCY_LABELS[form.urgency]}
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={5}
          value={form.urgency}
          onChange={(e) => onChange("urgency", Number(e.target.value))}
          className="w-full accent-primary"
        />
        <div className="mt-1 flex justify-between text-xs text-muted">
          <span>Low</span>
          <span>Medium</span>
          <span>Critical</span>
        </div>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium text-muted">Customer Budget (INR)</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted">₹</span>
          <input
            type="number"
            min={1}
            value={form.customer_budget}
            onChange={(e) => onChange("customer_budget", e.target.value)}
            className="w-full rounded-xl border border-border bg-background py-3 pl-10 pr-4 text-foreground outline-none focus:border-primary"
            required
          />
        </div>
      </div>

      <button type="submit" className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Finding matches..." : "Find Best Technicians →"}
      </button>
    </form>
  );
}
