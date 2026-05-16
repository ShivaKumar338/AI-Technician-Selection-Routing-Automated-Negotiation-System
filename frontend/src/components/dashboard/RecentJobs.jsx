import { Link } from "react-router-dom";
import { ArrowRight, ClipboardList } from "lucide-react";
import EmptyState from "../ui/EmptyState";
import StatusBadge from "../ui/StatusBadge";
import { Skeleton } from "../ui/Skeleton";
import { formatCurrency, formatDate } from "../../utils/format";

export default function RecentJobs({ jobs, loading }) {
  return (
    <div className="card-surface">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <h2 className="text-lg font-semibold text-foreground">Recent Jobs</h2>
        <Link to="/jobs/new" className="text-sm font-medium text-primary hover:underline">
          New →
        </Link>
      </div>
      <div className="divide-y divide-border">
        {loading && (
          <div className="space-y-3 p-5">
            {[1, 2, 3, 4].map((item) => (
              <Skeleton key={item} className="h-14 w-full" />
            ))}
          </div>
        )}
        {!loading && (!jobs || jobs.length === 0) && (
          <EmptyState
            icon={ClipboardList}
            title="No jobs yet"
            description="Create a new job to start matching technicians."
            action={
              <Link to="/jobs/new" className="btn-primary">
                Dispatch New Job
              </Link>
            }
          />
        )}
        {!loading &&
          jobs?.slice(0, 8).map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-background/50"
            >
              <div>
                <p className="font-medium text-foreground capitalize">{job.problem_type}</p>
                <p className="text-sm text-muted">
                  Budget {formatCurrency(job.customer_budget)} · {formatDate(job.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={job.status} />
                <ArrowRight className="h-4 w-4 text-muted" />
              </div>
            </Link>
          ))}
      </div>
    </div>
  );
}
