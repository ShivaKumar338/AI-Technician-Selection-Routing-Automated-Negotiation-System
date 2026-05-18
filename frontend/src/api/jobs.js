import api from "./axios";

export async function fetchJobs() {
  const { data } = await api.get("/jobs");
  return data.jobs || [];
}

export async function fetchJob(id) {
  const { data } = await api.get(`/jobs/${id}`);
  return data;
}

export async function fetchJobMessages(id) {
  const { data } = await api.get(`/jobs/${id}/messages`);
  return data.messages || [];
}

export async function createJob(payload) {
  const { data } = await api.post("/jobs", payload);
  return data;
}

export async function matchJob(jobId) {
  const { data } = await api.post(`/jobs/${jobId}/match`);
  return data;
}
