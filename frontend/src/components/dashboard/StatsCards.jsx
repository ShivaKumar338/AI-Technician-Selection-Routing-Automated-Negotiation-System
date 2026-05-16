import { Briefcase, CheckCircle2, IndianRupee, PiggyBank } from "lucide-react";
import { SkeletonCard } from "../ui/Skeleton";
import { formatCurrency } from "../../utils/format";

const cards = [
  { key: "total_jobs", label: "Total Jobs", icon: Briefcase },
  { key: "completed_jobs", label: "Completed", icon: CheckCircle2 },
  { key: "avg_agreed_price", label: "Avg Agreed Price", icon: IndianRupee, format: "currency" },
  { key: "total_savings", label: "Total Savings", icon: PiggyBank, format: "currency" },
];

export default function StatsCards({ stats, loading }) {
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <SkeletonCard key={card.key} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ key, label, icon: Icon, format }) => {
        const raw = stats?.[key] ?? 0;
        const value =
          format === "currency" ? formatCurrency(raw) : Number(raw).toLocaleString("en-IN");
        return (
          <div key={key} className="card-surface p-5 transition hover:border-primary/30">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium text-muted">{label}</span>
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <p className="text-2xl font-bold text-foreground">{value}</p>
          </div>
        );
      })}
    </div>
  );
}
