import api from "./axios";

export async function fetchJobs() {
  const { data } = await api.get("/jobs");
  return data.jobs || [];
}

export async function fetchJob(id) {
  const { data } = await api.get(`/jobs/${id}`);
  return data;
}

export async function createJob(payload) {
  const { data } = await api.post("/jobs", payload);
  return data;
}

export async function matchJob(jobId) {
  const { data } = await api.post(`/jobs/${jobId}/match`);
  return data;
}

export async function negotiateJob(jobId, techId) {
  const { data } = await api.post(`/jobs/${jobId}/negotiate/${techId}`);
  return data;
}
