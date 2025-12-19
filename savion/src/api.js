const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// --- Helper for fetch with error handling ---
async function handleResponse(r) {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`API error ${r.status}: ${text}`);
  }
  return r.json();
}

// --- Normalize MongoDB _id => id ---
function normalizeTxList(list) {
  return list.map((tx) => ({
    ...tx,
    id: tx.id || tx._id, // always ensure id exists
  }));
}

// --- TRANSACTIONS API ---

export async function listTx(userId) {
  const r = await fetch(`${API_BASE}/api/transactions?user_id=${userId}`);
  const data = await handleResponse(r);
  return normalizeTxList(data);
}

export async function createTx(tx) {
  const r = await fetch(`${API_BASE}/api/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tx),
  });
  return handleResponse(r);
}

export async function updateTx(id, tx) {
  if (!id) throw new Error("Missing transaction ID for update");

  const r = await fetch(`${API_BASE}/api/transactions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tx),
  });
  return handleResponse(r);
}

export async function deleteTx(id) {
  if (!id) throw new Error("Missing transaction ID for delete");

  const r = await fetch(`${API_BASE}/api/transactions/${id}`, {
    method: "DELETE",
  });
  return handleResponse(r);
}

// --- SUMMARY / FORECAST ---

export async function getSummary(userId, from, to) {
  const q = new URLSearchParams({
    user_id: userId,
    ...(from && { from }),
    ...(to && { to }),
  });

  const r = await fetch(`${API_BASE}/api/summary?${q.toString()}`);
  return handleResponse(r);
}

export async function getForecast(userId) {
  const r = await fetch(`${API_BASE}/api/predict?user_id=${userId}`);
  return handleResponse(r);
}

// --- CSV UPLOAD / EXPORT / TEMPLATE ---

export async function uploadCSV(userId, file) {
  const fd = new FormData();
  fd.append("file", file);

  const r = await fetch(`${API_BASE}/api/upload_csv?user_id=${userId}`, {
    method: "POST",
    body: fd,
  });
  return handleResponse(r);
}

export async function exportCSV(userId, from, to) {
  const q = new URLSearchParams({
    user_id: userId,
    ...(from && { from }),
    ...(to && { to }),
  });

  const r = await fetch(`${API_BASE}/api/export_csv?${q.toString()}`);
  return handleResponse(r);
}

export async function downloadTemplate() {
  const r = await fetch(`${API_BASE}/api/csv_template`);
  return handleResponse(r);
}

// --- GEMINI AI CHAT FUNCTIONS ---

export async function geminiChat(userId, query) {
  const r = await fetch(`${API_BASE}/api/gemini/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, query }),
  });
  return handleResponse(r);
}

export async function geminiAnalyze(userId) {
  const r = await fetch(`${API_BASE}/api/gemini/analyze/${userId}`);
  return handleResponse(r);
}

export async function clearGeminiHistory(userId) {
  const r = await fetch(`${API_BASE}/api/gemini/clear-history/${userId}`, {
    method: "DELETE",
  });
  return handleResponse(r);
}

export async function getConversationSummary(userId) {
  const r = await fetch(`${API_BASE}/api/gemini/conversation-summary/${userId}`);
  return handleResponse(r);
}

// --- WEB SOCKET STATUS ---

export async function getWebSocketStatus() {
  const r = await fetch(`${API_BASE}/api/websocket/status`);
  return handleResponse(r);
}

export async function sendNotification(userId, notification) {
  const r = await fetch(`${API_BASE}/api/websocket/notify/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(notification),
  });
  return handleResponse(r);
}
