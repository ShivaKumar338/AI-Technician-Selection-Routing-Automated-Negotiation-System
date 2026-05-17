import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, User, MessageCircle } from "lucide-react";
import { fetchJob } from "../api/jobs";
import api from "../api/axios";
import PageHeader from "../components/ui/PageHeader";
import StatusBadge from "../components/ui/StatusBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { formatCurrency, formatDate } from "../utils/format";

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [waMsgs, setWaMsgs] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJob(id);
      setJob(data);
      // Load WhatsApp negotiation messages if any session exists
      try {
        const { data: sessions } = await api.get(`/api/negotiate/sessions?job_id=${id}`);
        if (sessions.sessions?.length) {
          const sid = sessions.sessions[0].id;
          const { data: msgs } = await api.get(`/api/negotiate/sessions/${sid}/messages`);
          setWaMsgs(msgs.messages || []);
        }
      } catch (_) {}
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-60 w-full" />
      </div>
    );
  }

  if (!job) return <p className="text-muted">Job not found.</p>;

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
              <p className="font-semibold">{job.customer_lat}, {job.customer_lng}</p>
            </div>
            <div>
              <p className="text-muted">Agreed Price</p>
              <p className="font-semibold text-primary">{formatCurrency(job.agreed_price)}</p>
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

      {/* WhatsApp negotiation chat log */}
      <div className="card-surface p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <MessageCircle className="h-5 w-5 text-[#25D366]" />
          WhatsApp Negotiation
        </h2>
        {waMsgs.length === 0 ? (
          <p className="text-muted text-sm">No WhatsApp messages yet.</p>
        ) : (
          <div className="space-y-2">
            {waMsgs.map((m) => {
              const isAI = m.sender === "ai";
              const isSystem = m.sender === "system";
              return (
                <div
                  key={m.id}
                  className={`flex ${isAI ? "justify-end" : isSystem ? "justify-center" : "justify-start"}`}
                >
                  {isSystem ? (
                    <span className="text-xs text-muted italic">{m.message}</span>
                  ) : (
                    <div
                      className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                        isAI
                          ? "bg-primary/20 text-foreground rounded-br-sm"
                          : "bg-card border border-border text-foreground rounded-bl-sm"
                      }`}
                    >
                      <p className={`text-[10px] font-semibold mb-1 ${isAI ? "text-primary" : "text-[#25D366]"}`}>
                        {isAI ? "AI Agent" : "Technician"}
                        {m.our_offer ? ` · ₹${m.our_offer}` : ""}
                        {m.their_offer ? ` · ₹${m.their_offer}` : ""}
                      </p>
                      <p>{m.message}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
