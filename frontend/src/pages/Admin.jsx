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

function ReportCard({ report, children }) {
  return (
    <article className="card" style={{ marginTop: 14 }}>
      <p className="small muted">
        {SCAM_TYPE_LABELS[report.scam_type]} · {OUTCOME_LABELS[report.outcome]} · checker said {report.verdict} · {report.created_at}
      </p>
      <pre className="evidence">{report.story}</pre>
      <p className="small"><strong>Signals:</strong> {report.signals.join(", ") || "none"}</p>
      <p className="small"><strong>Links:</strong> {report.entities.map((e) => e.display).join(", ") || "none"}</p>
      {children}
    </article>
  );
}

export default function Admin() {
  const [token, setToken] = useState(savedToken);
  const [reports, setReports] = useState(null);
  const [published, setPublished] = useState([]);
  const [error, setError] = useState("");

  async function load(e) {
    e?.preventDefault();
    setError("");
    try {
      const data = await api.pending(token);
      setReports(data.reports);
      setPublished(data.published || []);
      try { sessionStorage.setItem("cc-admin", token); } catch { /* storage unavailable */ }
    } catch (err) {
      setError(err.message);
      setReports(null);
      setPublished([]);
    }
  }

  async function review(id, action) {
    try {
      await api.review(token, id, action);
      setReports(reports.filter((r) => r.id !== id));
      setPublished(published.filter((r) => r.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <div className="wrap">
        <PageHeading eyebrow="Moderation" title="Review queue">
          Stories are published automatically unless code or the AI screen finds a reason to hold them. Held stories wait here for you; you can also take down anything published.
        </PageHeading>
        <form className="btn-row" onSubmit={load}>
          <label className="sr-only" htmlFor="token">Admin token</label>
          <input id="token" type="password" value={token} onChange={(e) => setToken(e.target.value)}
            placeholder="Admin token" style={{ flex: "1 1 240px" }} autoComplete="off" />
          <button className="btn">Load reports</button>
        </form>
        {error && <p className="error" role="alert" style={{ marginTop: 14 }}>{error}</p>}

        {reports && (
          <>
            <h2 style={{ marginTop: 28 }}>Held for review ({reports.length})</h2>
            {reports.length === 0 && <p>Nothing waiting for review.</p>}
            {reports.map((r) => (
              <ReportCard report={r} key={r.id}>
                <p className="small" style={{ marginBottom: 4 }}><strong>Held because:</strong></p>
                <ul className="small" style={{ marginTop: 0 }}>
                  {(r.held || []).map((h, i) => (
                    <li key={i}>{h.label}{h.quote ? `: "${h.quote}"` : ""}</li>
                  ))}
                  {!r.held?.length && <li>Sent before automatic screening</li>}
                </ul>
                <p className="small muted">Check: no personal details left, no claims that a licensed firm is a scam, no "this is legit" posts.</p>
                <div className="btn-row">
                  <button className="btn" onClick={() => review(r.id, "approve")}>Approve and publish</button>
                  <button className="btn quiet" onClick={() => review(r.id, "reject")}>Reject</button>
                </div>
              </ReportCard>
            ))}

            <h2 style={{ marginTop: 28 }}>Published automatically ({published.length})</h2>
            {published.length === 0 && <p>No stories have been published automatically yet.</p>}
            {published.map((r) => (
              <ReportCard report={r} key={r.id}>
                <div className="btn-row">
                  <button className="btn quiet" onClick={() => review(r.id, "reject")}>Take down</button>
                </div>
              </ReportCard>
            ))}
          </>
        )}
      </div>
    </section>
  );
}
