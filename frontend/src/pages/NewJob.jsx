import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { createJob, matchJob } from "../api/jobs";
import api from "../api/axios";
import JobForm from "../components/jobs/JobForm";
import MatchResults from "../components/jobs/MatchResults";
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
  const [whatsappId, setWhatsappId] = useState(null);

  const onChange = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

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

  const onWhatsApp = async (tech) => {
    if (!jobId) return toast.error("Create a job first");
    setWhatsappId(tech.id);
    try {
      const { data } = await api.post(`/api/negotiate/${jobId}?tech_id=${tech.id}`);
      toast.success(`WhatsApp negotiation started with ${data.technician_name}`);
      navigate(`/jobs/${jobId}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message);
    } finally {
      setWhatsappId(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dispatch New Job"
        subtitle="Create a service request and let AI negotiate via WhatsApp"
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <JobForm form={form} onChange={onChange} onSubmit={onSubmit} submitting={submitting} />
        <div className="card-surface p-6">
          <h2 className="mb-1 text-lg font-semibold text-foreground">Top Matched Technicians</h2>
          <p className="mb-4 text-sm text-muted">Ranked by skill match, distance, and rating</p>
          <MatchResults
            matches={matches}
            onWhatsApp={onWhatsApp}
            whatsappId={whatsappId}
          />
        </div>
      </div>
    </div>
  );
}
