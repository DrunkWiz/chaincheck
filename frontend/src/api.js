async function request(method, path, body, headers = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json", ...headers } : headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Can't reach ChainCheck. Check your connection and try again.");
  }
  let data = {};
  try {
    data = await response.json();
  } catch {
    /* empty body */
  }
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

export const api = {
  meta: () => request("GET", "/api/meta"),
  analyze: (payload) => request("POST", "/api/analyze", payload),
  reports: (q = "", type = "") =>
    request("GET", `/api/reports?${new URLSearchParams({ q, type })}`),
  preview: (story) => request("POST", "/api/reports/preview", { story }),
  submit: (payload) => request("POST", "/api/reports", payload),
  helped: (id) => request("POST", `/api/reports/${id}/helped`),
  pending: (token) => request("GET", "/api/admin/reports", null, { "X-Admin-Token": token }),
  review: (token, id, action) =>
    request("POST", `/api/admin/reports/${id}/${action}`, {}, { "X-Admin-Token": token }),
};

export const SCAM_TYPE_LABELS = {
  fake_trading_platform: "Fake trading platform",
  crypto: "Crypto scheme",
  romance_investment: "Romance turned investment",
  ai_trading_group: "\"AI trading\" group",
  copycat_firm: "Copycat of a real firm",
  fund_recovery: "\"Fund recovery\"",
  other: "Other",
};

export const OUTCOME_LABELS = {
  lost_money: "Lost money",
  stopped_in_time: "Stopped in time",
  still_happening: "Still happening",
  recovered_some: "Recovered some",
};
