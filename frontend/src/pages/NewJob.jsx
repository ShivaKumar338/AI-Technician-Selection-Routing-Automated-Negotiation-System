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
  customer_name: "",
  customer_phone: "",
  customer_address: "",
  visit_date: "",
  visit_time: "",
  urgency: 3,
  customer_budget: "",
  description: "",
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
        urgency: Number(form.urgency),
        customer_budget: Number(form.customer_budget),
        customer_name: form.customer_name || null,
        customer_phone: form.customer_phone || null,
        customer_address: form.customer_address || null,
        visit_date: form.visit_date || null,
        visit_time: form.visit_time || null,
        description: form.description || null,
        // lat/lng default to Hyderabad on backend — no need to send
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
        subtitle="Fill in customer details and let AI negotiate via WhatsApp"
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
