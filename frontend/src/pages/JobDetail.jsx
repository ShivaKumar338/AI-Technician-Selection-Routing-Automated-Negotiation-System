import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, User, MessageCircle, Loader2, CalendarCheck, DollarSign, CheckCircle2, RefreshCw } from "lucide-react";
import { fetchJob } from "../api/jobs";
import api from "../api/axios";
import PageHeader from "../components/ui/PageHeader";
import StatusBadge from "../components/ui/StatusBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { formatCurrency, formatDate } from "../utils/format";

const POLL_MS = 2000;

function deriveStage(messages, jobStatus) {
  if (jobStatus === "assigned") return "dispatched";
  const aiMsgs = messages.filter((m) => m.sender === "ai");
  if (aiMsgs.length === 0) return null;
  const hasPriceMsg = aiMsgs.some((m) => m.our_offer != null);
  return hasPriceMsg ? "negotiating" : "availability";
}

function StageIndicator({ messages, jobStatus }) {
  const stage = deriveStage(messages, jobStatus);
  if (!stage) return null;

  const stages = [
    { key: "availability", label: "Availability", icon: CalendarCheck },
    { key: "negotiating",  label: "Negotiating",  icon: DollarSign },
    { key: "dispatched",   label: "Dispatched",   icon: CheckCircle2 },
  ];
  const activeIdx = stages.findIndex((s) => s.key === stage);

  return (
    <div className="flex items-center gap-1">
      {stages.map((s, i) => {
        const Icon = s.icon;
        const done = i < activeIdx;
        const active = i === activeIdx;
        return (
          <div key={s.key} className="flex items-center gap-1">
            <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              active ? "bg-amber-400/20 text-amber-300" :
              done   ? "bg-primary/15 text-primary" :
                       "bg-border/40 text-muted"
            }`}>
              <Icon className="h-3 w-3" />
              {s.label}
            </span>
            {i < stages.length - 1 && <span className="text-muted/40 text-xs">›</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState([]);
  const [msgError, setMsgError] = useState(false);
  const chatEndRef = useRef(null);
  const isFirstLoad = useRef(true);

  const loadJob = useCallback(async () => {
    try {
      const data = await fetchJob(id);
      setJob(data);
    } catch (err) {
      if (isFirstLoad.current) toast.error(err.message);
    }
  }, [id]);

  const loadMessages = useCallback(async () => {
    try {
      const { data } = await api.get(`/jobs/${id}/messages`);
      setMessages(data.messages || []);
      setMsgError(false);
    } catch (err) {
      console.error("loadMessages:", err?.message);
      setMsgError(true);
    }
  }, [id]);

  // Initial load
  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadJob(), loadMessages()]);
      setLoading(false);
      isFirstLoad.current = false;
    })();
  }, [loadJob, loadMessages]);

  // Live polling
  useEffect(() => {
    const interval = setInterval(() => {
      loadJob();
      loadMessages();
    }, POLL_MS);
    return () => clearInterval(interval);
  }, [loadJob, loadMessages]);

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (!job) return <p className="text-muted">Job not found.</p>;

  const isNegotiating = job.status === "negotiating";
  const isDone = job.status === "assigned";

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
        {/* Job info */}
        <div className="card-surface space-y-4 p-6">
          <h2 className="text-lg font-semibold">Job Information</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {job.customer_name && (
              <div>
                <p className="text-muted">Customer</p>
                <p className="font-semibold">{job.customer_name}</p>
              </div>
            )}
            {job.customer_phone && (
              <div>
                <p className="text-muted">Phone</p>
                <p className="font-semibold">{job.customer_phone}</p>
              </div>
            )}
            <div>
              <p className="text-muted">Budget</p>
              <p className="font-semibold">{formatCurrency(job.customer_budget)}</p>
            </div>
            <div>
              <p className="text-muted">Urgency</p>
              <p className="font-semibold">{job.urgency}/5</p>
            </div>
            {job.visit_date && (
              <div>
                <p className="text-muted">Visit</p>
                <p className="font-semibold">
                  {job.visit_date}{job.visit_time ? ` at ${job.visit_time}` : ""}
                </p>
              </div>
            )}
            <div>
              <p className="text-muted">Agreed Price</p>
              <p className="font-semibold text-primary">
                {job.agreed_price ? formatCurrency(job.agreed_price) : "—"}
              </p>
            </div>
          </div>
          {job.customer_address && (
            <div className="rounded-xl border border-border bg-background/50 p-3">
              <p className="text-xs text-muted mb-1">Service Address</p>
              <p className="text-sm">{job.customer_address}</p>
            </div>
          )}
          {job.description && (
            <div className="rounded-xl border border-border bg-background/50 p-3">
              <p className="text-xs text-muted mb-1">Problem Description</p>
              <p className="text-sm">{job.description}</p>
            </div>
          )}
        </div>

        {/* Assigned technician */}
        <div className="card-surface space-y-4 p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <User className="h-5 w-5 text-primary" />
            Assigned Technician
          </h2>
          {job.technician_name ? (
            <div>
              <p className="text-xl font-bold">{job.technician_name}</p>
              <p className="text-sm text-muted">ID: {job.assigned_tech_id}</p>
              {job.agreed_price && (
                <p className="mt-2 text-sm font-semibold text-primary">
                  Deal closed at {formatCurrency(job.agreed_price)}
                </p>
              )}
            </div>
          ) : (
            <p className="text-muted">No technician assigned yet.</p>
          )}
        </div>
      </div>

      {/* Live WhatsApp chat */}
      <div className="card-surface flex flex-col" style={{ minHeight: "420px" }}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <MessageCircle className="h-5 w-5 text-[#25D366]" />
            WhatsApp Negotiation
            {messages.length > 0 && (
              <span className="text-xs text-muted font-normal">({messages.length} messages)</span>
            )}
          </h2>
          <div className="flex items-center gap-3">
            {isNegotiating && (
              <>
                <StageIndicator messages={messages} jobStatus={job.status} />
                <span className="flex items-center gap-1.5 text-xs text-[#25D366]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Live
                </span>
              </>
            )}
            {isDone && messages.length > 0 && (
              <span className="rounded-full bg-primary/15 px-3 py-1 text-xs font-semibold text-primary">
                Deal Closed ✓
              </span>
            )}
            {msgError && (
              <button
                onClick={loadMessages}
                className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300"
              >
                <RefreshCw className="h-3 w-3" />
                Retry
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3" style={{ maxHeight: "500px" }}>
          {msgError ? (
            <p className="text-center text-sm text-amber-400 py-8">
              Could not load messages. Check backend connection.
            </p>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              {isNegotiating ? (
                <>
                  <Loader2 className="h-6 w-6 animate-spin text-[#25D366]" />
                  <p className="text-sm text-muted">Negotiation in progress — messages will appear here</p>
                </>
              ) : (
                <p className="text-sm text-muted">No WhatsApp messages for this job yet.</p>
              )}
            </div>
          ) : (
            messages.map((m) => {
              const isAI = m.sender === "ai";
              const isSystem = m.sender === "system";
              return (
                <div
                  key={m.id}
                  className={`flex ${isAI ? "justify-end" : isSystem ? "justify-center" : "justify-start"}`}
                >
                  {isSystem ? (
                    <span className="text-xs text-muted italic bg-background/50 px-3 py-1 rounded-full border border-border">
                      {m.message}
                    </span>
                  ) : (
                    <div className={`max-w-[72%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                      isAI
                        ? "bg-primary/20 text-foreground rounded-br-none"
                        : "bg-card border border-border text-foreground rounded-bl-none"
                    }`}>
                      <p className={`text-[10px] font-semibold mb-1 ${isAI ? "text-primary" : "text-[#25D366]"}`}>
                        {isAI ? "AI Agent" : "Technician"}
                        {m.our_offer ? ` · offered ₹${m.our_offer}` : ""}
                        {m.their_offer ? ` · asked ₹${m.their_offer}` : ""}
                      </p>
                      <p className="leading-relaxed whitespace-pre-line">{m.message}</p>
                      <p className="text-[10px] text-muted/60 mt-1 text-right">
                        {new Date(m.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  )}
                </div>
              );
            })
          )}
          <div ref={chatEndRef} />
        </div>
      </div>
    </div>
  );
}
