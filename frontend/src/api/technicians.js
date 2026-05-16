import api from "./axios";

export async function fetchTechnicians() {
  const { data } = await api.get("/technicians");
  return data.technicians || [];
}

export async function createTechnician(payload) {
  const { data } = await api.post("/technicians", payload);
  return data;
}

export async function seedTechnicians() {
  const { data } = await api.post("/seed");
  return data;
}
