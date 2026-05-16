import { Search } from "lucide-react";
import { SKILL_FILTERS } from "../../utils/problemTypes";
import { cn } from "../../utils/cn";

export default function TechnicianFilters({
  search,
  onSearchChange,
  skill,
  onSkillChange,
  availableOnly,
  onAvailableOnlyChange,
}) {
  return (
    <div className="card-surface flex flex-col gap-4 p-4 lg:flex-row lg:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Search by name or skill..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full rounded-xl border border-border bg-background py-3 pl-10 pr-4 text-foreground outline-none focus:border-primary"
        />
      </div>
      <div className="flex flex-wrap gap-2">
        {SKILL_FILTERS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onSkillChange(skill === item ? "" : item)}
            className={cn(
              "rounded-xl border px-3 py-2 text-sm capitalize transition",
              skill === item
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-muted hover:border-primary/40"
            )}
          >
            {item}
          </button>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm text-muted">
        <input
          type="checkbox"
          checked={availableOnly}
          onChange={(e) => onAvailableOnlyChange(e.target.checked)}
          className="accent-primary"
        />
        Available only
      </label>
    </div>
  );
}
