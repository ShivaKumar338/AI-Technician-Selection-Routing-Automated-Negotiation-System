import { cn } from "../../utils/cn";

export function Skeleton({ className }) {
  return (
    <div className={cn("animate-pulse rounded-xl bg-border/60", className)} />
  );
}

export function SkeletonCard() {
  return (
    <div className="card-surface p-5">
      <Skeleton className="mb-3 h-4 w-24" />
      <Skeleton className="h-8 w-16" />
    </div>
  );
}
