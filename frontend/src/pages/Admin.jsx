import PageHeading from "../components/PageHeading.jsx";
import { useState } from "react";
import { api, OUTCOME_LABELS, SCAM_TYPE_LABELS } from "../api.js";

function savedToken() {
  try {
    return sessionStorage.getItem("cc-admin") || "";
  } catch {
    return "";
  }
}

export default function Admin() {
  const [token, setToken] = useState(savedToken);
  const [reports, setReports] = useState(null);
  const [error, setError] = useState("");

  async function load(e) {
    e?.preventDefault();
    setError("");
    try {
      const data = await api.pending(token);
      setReports(data.reports);
      try { sessionStorage.setItem("cc-admin", token); } catch { /* storage unavailable */ }
    } catch (err) {
      setError(err.message);
      setReports(null);
    }
  }

  async function review(id, action) {
    try {
      await api.review(token, id, action);
      setReports(reports.filter((r) => r.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <div className="wrap">
        <PageHeading eyebrow="Moderation" title="Review queue">Review personal details and evidence before publishing a story.</PageHeading>
        <form className="btn-row" onSubmit={load}>
          <label className="sr-only" htmlFor="token">Admin token</label>
          <input id="token" type="password" value={token} onChange={(e) => setToken(e.target.value)}
            placeholder="Admin token" style={{ flex: "1 1 240px" }} autoComplete="off" />
          <button className="btn">Load pending reports</button>
        </form>
        {error && <p className="error" role="alert" style={{ marginTop: 14 }}>{error}</p>}
        {reports && reports.length === 0 && <p style={{ marginTop: 18 }}>Nothing waiting for review.</p>}
        {reports?.map((r) => (
          <article className="card" key={r.id} style={{ marginTop: 14 }}>
            <p className="small muted">
              {SCAM_TYPE_LABELS[r.scam_type]} · {OUTCOME_LABELS[r.outcome]} · checker said {r.verdict} · {r.created_at}
            </p>
            <pre className="evidence">{r.story}</pre>
            <p className="small"><strong>Signals:</strong> {r.signals.join(", ") || "none"}</p>
            <p className="small"><strong>Links:</strong> {r.entities.map((e) => e.display).join(", ") || "none"}</p>
            <p className="small muted">Check: no personal details left, no claims that a licensed firm is a scam, no "this is legit" posts.</p>
            <div className="btn-row">
              <button className="btn" onClick={() => review(r.id, "approve")}>Approve and publish</button>
              <button className="btn quiet" onClick={() => review(r.id, "reject")}>Reject</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
