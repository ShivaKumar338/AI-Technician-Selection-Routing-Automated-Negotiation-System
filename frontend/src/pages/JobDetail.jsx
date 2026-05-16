import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, User } from "lucide-react";
import { fetchJob } from "../api/jobs";
import PageHeader from "../components/ui/PageHeader";
import StatusBadge from "../components/ui/StatusBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { formatCurrency, formatDate } from "../utils/format";

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJob(id);
      setJob(data);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-60 w-full" />
      </div>
    );
  }

  if (!job) {
    return <p className="text-muted">Job not found.</p>;
  }

  const logs = job.negotiation_logs || [];

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-primary">
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>
      <PageHeader
        title={`${job.problem_type} Service Job`}
        subtitle={`Created ${formatDate(job.created_at)}`}
        action={<StatusBadge status={job.status} />}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-surface space-y-4 p-6">
          <h2 className="text-lg font-semibold">Job Information</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted">Budget</p>
              <p className="font-semibold">{formatCurrency(job.customer_budget)}</p>
            </div>
            <div>
              <p className="text-muted">Urgency</p>
              <p className="font-semibold">{job.urgency}/5</p>
            </div>
            <div>
              <p className="text-muted">Location</p>
              <p className="font-semibold">
                {job.customer_lat}, {job.customer_lng}
              </p>
            </div>
            <div>
              <p className="text-muted">Agreed Price</p>
              <p className="font-semibold text-primary">
                {formatCurrency(job.agreed_price)}
              </p>
            </div>
          </div>
        </div>

        <div className="card-surface space-y-4 p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <User className="h-5 w-5 text-primary" />
            Assigned Technician
          </h2>
          {job.technician_name ? (
            <div>
              <p className="text-xl font-bold text-foreground">{job.technician_name}</p>
              <p className="text-sm text-muted">ID: {job.assigned_tech_id}</p>
            </div>
          ) : (
            <p className="text-muted">No technician assigned yet.</p>
          )}
        </div>
      </div>

      <div className="card-surface p-6">
        <h2 className="mb-4 text-lg font-semibold">Negotiation Log</h2>
        {logs.length === 0 ? (
          <p className="text-muted">No negotiation rounds recorded.</p>
        ) : (
          <div className="space-y-4">
            {logs.map((round) => (
              <div
                key={round.id || round.round}
                className="rounded-xl border border-border bg-background p-4"
              >
                <p className="mb-2 font-medium">Round {round.round}</p>
                <div className="grid gap-3 sm:grid-cols-2 text-sm">
                  <div>
                    <p className="text-primary">Customer: {formatCurrency(round.customer_offer)}</p>
                    <p className="text-muted">{round.customer_message}</p>
                  </div>
                  <div>
                    <p className="text-secondary">
                      Technician: {formatCurrency(round.tech_offer)}
                    </p>
                    <p className="text-muted">{round.tech_message}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
