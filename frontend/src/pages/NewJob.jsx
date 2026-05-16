import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { createJob, matchJob, negotiateJob } from "../api/jobs";
import JobForm from "../components/jobs/JobForm";
import MatchResults from "../components/jobs/MatchResults";
import NegotiationModal from "../components/negotiation/NegotiationModal";
import PageHeader from "../components/ui/PageHeader";

const INITIAL_FORM = {
  problem_type: "AC",
  customer_lat: 17.385,
  customer_lng: 78.4867,
  urgency: 3,
  customer_budget: 1500,
};

export default function NewJob() {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [matches, setMatches] = useState([]);
  const [negotiatingId, setNegotiatingId] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [negotiationResult, setNegotiationResult] = useState(null);
  const [negotiationLoading, setNegotiationLoading] = useState(false);

  const onChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMatches([]);
    try {
      const payload = {
        problem_type: form.problem_type,
        customer_lat: Number(form.customer_lat),
        customer_lng: Number(form.customer_lng),
        urgency: Number(form.urgency),
        customer_budget: Number(form.customer_budget),
      };
      const job = await createJob(payload);
      setJobId(job.id);
      toast.success("Job created");

      const matchData = await matchJob(job.id);
      setMatches(matchData.technicians || []);
      toast.success("Top technicians matched");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const onNegotiate = async (tech) => {
    if (!jobId) return;
    setNegotiatingId(tech.id);
    setNegotiationLoading(true);
    setModalOpen(true);
    setNegotiationResult(null);
    try {
      const result = await negotiateJob(jobId, tech.id);
      setNegotiationResult(result);
      toast.success(`Agreed at ${result.agreed_price} INR with ${result.technician_name}`);
    } catch (error) {
      toast.error(error.message);
      setModalOpen(false);
    } finally {
      setNegotiatingId(null);
      setNegotiationLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    if (negotiationResult && jobId) {
      navigate(`/jobs/${jobId}`);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dispatch New Job"
        subtitle="Create a service request and let AI agents negotiate the best deal"
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <JobForm form={form} onChange={onChange} onSubmit={onSubmit} submitting={submitting} />
        <div className="card-surface p-6">
          <h2 className="mb-1 text-lg font-semibold text-foreground">Top Matched Technicians</h2>
          <p className="mb-4 text-sm text-muted">
            Ranked by skill match, distance, and rating
          </p>
          <MatchResults
            matches={matches}
            onNegotiate={onNegotiate}
            negotiatingId={negotiatingId}
          />
        </div>
      </div>
      <NegotiationModal
        open={modalOpen}
        onClose={closeModal}
        result={negotiationResult}
        loading={negotiationLoading}
      />
    </div>
  );
}
