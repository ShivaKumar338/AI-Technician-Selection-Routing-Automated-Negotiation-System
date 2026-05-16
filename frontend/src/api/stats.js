import api from "./axios";

export async function fetchStats() {
  const { data } = await api.get("/stats");
  return data;
}
