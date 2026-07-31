const BASE = '/api/v1'

async function handle(response) {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail)
  }
  return response.json()
}

const json = (path, body, method = 'POST') =>
  fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle)

export const api = {
  analyzeText: (text, sourceType = 'text') => json('/intake/analyze', { text, source_type: sourceType }),

  analyzeFile: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/intake/upload`, { method: 'POST', body: form }).then(handle)
  },

  correct: (threadId, message) => json('/intake/correct', { thread_id: threadId, message }),

  saveComplaint: (payload) => json('/complaints', payload),
  listComplaints: (params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
    return fetch(`${BASE}/complaints${query ? `?${query}` : ''}`).then(handle)
  },
  getComplaint: (id) => fetch(`${BASE}/complaints/${id}`).then(handle),
  stats: () => fetch(`${BASE}/complaints/stats`).then(handle),
  updateStatus: (id, status, reason) => json(`/complaints/${id}/status`, { status, reason }, 'PATCH'),

  ask: (question, complaintId) => json('/copilot/ask', { question, complaint_id: complaintId ?? null }),
  reference: () => fetch(`${BASE}/meta/reference`).then(handle),
  graph: () => fetch(`${BASE}/meta/graph`).then(handle),
}
