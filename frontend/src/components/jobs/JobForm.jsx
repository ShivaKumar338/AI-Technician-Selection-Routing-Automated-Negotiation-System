import { PROBLEM_TYPES } from "../../utils/problemTypes";
import { cn } from "../../utils/cn";
import { User, Phone, MapPin, Calendar, Clock, IndianRupee, AlertTriangle } from "lucide-react";

const URGENCY_LABELS = { 1: "Low", 2: "Low-Med", 3: "Medium", 4: "High", 5: "Critical" };
const URGENCY_COLORS = {
  1: "text-green-400 bg-green-400/10",
  2: "text-lime-400 bg-lime-400/10",
  3: "text-amber-400 bg-amber-400/10",
  4: "text-orange-400 bg-orange-400/10",
  5: "text-red-400 bg-red-400/10",
};

function Field({ label, required, children }) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-muted">
        {label}
        {required && <span className="ml-1 text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}

function Input({ icon: Icon, ...props }) {
  return (
    <div className="relative">
      {Icon && (
        <Icon className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted/60 pointer-events-none" />
      )}
      <input
        {...props}
        className={cn(
          "w-full rounded-xl border border-border bg-background py-3 text-foreground outline-none focus:border-primary transition text-sm",
          Icon ? "pl-10 pr-4" : "px-4"
        )}
      />
    </div>
  );
}

export default function JobForm({ form, onChange, onSubmit, submitting }) {
  return (
    <form onSubmit={onSubmit} className="card-surface space-y-5 p-6">

      {/* Problem type */}
      <Field label="Service Type" required>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {PROBLEM_TYPES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => onChange("problem_type", value)}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-xl border p-3 transition",
                form.problem_type === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-background text-muted hover:border-primary/40"
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="text-xs font-medium">{label}</span>
            </button>
          ))}
        </div>
      </Field>

      {/* Customer name + phone */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Customer Name" required>
          <Input
            icon={User}
            type="text"
            placeholder="Ravi Kumar"
            value={form.customer_name}
            onChange={(e) => onChange("customer_name", e.target.value)}
            required
          />
        </Field>
        <Field label="Phone Number" required>
          <Input
            icon={Phone}
            type="tel"
            placeholder="9876543210"
            value={form.customer_phone}
            onChange={(e) => onChange("customer_phone", e.target.value)}
            required
          />
        </Field>
      </div>

      {/* Address */}
      <Field label="Service Address" required>
        <div className="relative">
          <MapPin className="absolute left-3.5 top-3.5 h-4 w-4 text-muted/60 pointer-events-none" />
          <textarea
            rows={2}
            placeholder="Flat 4B, Sunshine Apartments, Banjara Hills"
            value={form.customer_address}
            onChange={(e) => onChange("customer_address", e.target.value)}
            required
            className="w-full rounded-xl border border-border bg-background py-3 pl-10 pr-4 text-foreground outline-none focus:border-primary resize-none text-sm placeholder:text-muted/50 transition"
          />
        </div>
      </Field>

      {/* Visit date + time */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Preferred Visit Date">
          <Input
            icon={Calendar}
            type="date"
            value={form.visit_date}
            onChange={(e) => onChange("visit_date", e.target.value)}
            min={new Date().toISOString().split("T")[0]}
          />
        </Field>
        <Field label="Preferred Time">
          <Input
            icon={Clock}
            type="time"
            value={form.visit_time}
            onChange={(e) => onChange("visit_time", e.target.value)}
          />
        </Field>
      </div>

      {/* Budget + urgency */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Budget (INR)" required>
          <div className="relative">
            <IndianRupee className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted/60 pointer-events-none" />
            <input
              type="number"
              min={1}
              placeholder="1500"
              value={form.customer_budget}
              onChange={(e) => onChange("customer_budget", e.target.value)}
              required
              className="w-full rounded-xl border border-border bg-background py-3 pl-10 pr-4 text-foreground outline-none focus:border-primary transition text-sm"
            />
          </div>
        </Field>

        <Field label="Urgency">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Low → Critical</span>
              <span className={cn("rounded-lg px-2 py-0.5 text-xs font-semibold", URGENCY_COLORS[form.urgency])}>
                <AlertTriangle className="inline h-3 w-3 mr-1" />
                {URGENCY_LABELS[form.urgency]}
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
          </div>
        </Field>
      </div>

      {/* Description */}
      <Field label="Problem Description">
        <textarea
          rows={3}
          value={form.description}
          onChange={(e) => onChange("description", e.target.value)}
          placeholder='e.g. "AC not cooling, drainage leakage from indoor unit"'
          className="w-full rounded-xl border border-border bg-background px-4 py-3 text-foreground outline-none focus:border-primary resize-none text-sm placeholder:text-muted/50 transition"
        />
      </Field>

      <button type="submit" className="btn-primary w-full py-3 text-sm font-semibold" disabled={submitting}>
        {submitting ? "Finding matches..." : "Find Best Technicians →"}
      </button>
    </form>
  );
}
