import axios from "axios";

const client = axios.create({ baseURL: "/api", timeout: 30000 });

export async function fetchInteraction(sessionId) {
  const res = await client.get(`/interaction/${sessionId}`);
  return res.data;
}

export async function sendChatMessage(sessionId, message, history) {
  const res = await client.post("/chat", { session_id: sessionId, message, history });
  return res.data;
}

export async function resetInteraction(sessionId) {
  const res = await client.post(`/reset/${sessionId}`);
  return res.data;
}