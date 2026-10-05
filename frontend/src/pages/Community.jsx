import { useEffect, useState } from "react";
import { api, OUTCOME_LABELS, SCAM_TYPE_LABELS } from "../api.js";

function ReportCard({ report }) {
  const [helped, setHelped] = useState(report.helped);
  const [clicked, setClicked] = useState(false);
  return (
    <article className="card report-card">
      <div className="meta">
        <span className="tag">{SCAM_TYPE_LABELS[report.scam_type] || report.scam_type}</span>
        <span className="tag">{OUTCOME_LABELS[report.outcome] || report.outcome}</span>
        {report.verdict === "STOP" && <span className="tag" style={{ background: "#FBECEB", color: "#A3241A" }}>✕ Checker said STOP</span>}
        {report.synthetic && <span className="tag synthetic">SYNTHETIC demo report</span>}
      </div>
      <p className="story">{report.story}</p>
      {report.signals.length > 0 && (
        <p className="small"><strong>Signals:</strong> {report.signals.join(" · ")}</p>
      )}
      {report.entities.length > 0 && (
        <>
          <p className="small" style={{ margin: 0 }}><strong>Linked details</strong></p>
          <ul className="entity-list">
            {report.entities.map((e) => <li key={`${e.kind}-${e.display}`}>{e.display}</li>)}
          </ul>
        </>
      )}
      {report.network_size > 1 && (
        <p className="small" style={{ color: "#A3241A", fontWeight: 700 }}>
          Linked to {report.network_size - 1} other {report.network_size === 2 ? "report" : "reports"} by shared details.
        </p>
      )}
      <button type="button" className="btn quiet" disabled={clicked}
        onClick={() => { setClicked(true); setHelped(helped + 1); api.helped(report.id).catch(() => {}); }}>
        This helped me {helped > 0 ? `(${helped})` : ""}
      </button>
    </article>
  );
}

export default function Community() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  function load(q = query, t = type) {
    setError("");
    api.reports(q, t).then(setData).catch((e) => setError(e.message));
  }

  useEffect(() => { load("", ""); }, []);

  return (
    <section>
      <div className="wrap wide">
        <p className="eyebrow">Community reports</p>
        <h1>What happened to others</h1>
        <p className="muted">
          Real stories of what went wrong, with personal details removed and every report reviewed before it's
          published. Search for a website, app, company or wallet you've been sent.
        </p>
        <form className="btn-row" role="search" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <label className="sr-only" htmlFor="search">Search reports</label>
          <input id="search" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. novaapex.example or a wallet address" style={{ flex: "1 1 260px" }} />
          <button className="btn">Search</button>
        </form>
        <div className="filters" aria-label="Filter by scam type">
          <button type="button" className="chip" aria-pressed={type === ""} onClick={() => { setType(""); load(query, ""); }}>All</button>
          {Object.entries(SCAM_TYPE_LABELS).map(([k, l]) => (
            <button key={k} type="button" className="chip" aria-pressed={type === k}
              onClick={() => { setType(k); load(query, k); }}>{l}</button>
          ))}
        </div>
        {error && <p className="error" role="alert">{error}</p>}

        <div className="community-layout">
          <div>
            {data && data.reports.length === 0 && <p>No reports match that yet.</p>}
            {data?.reports.map((r) => <ReportCard key={r.id} report={r} />)}
          </div>
          <aside>
            <h2 style={{ fontSize: "1.3rem" }}>Network alerts</h2>
            {data?.alerts.length === 0 && <p className="small">No linked groups yet.</p>}
            {data?.alerts.slice(0, 3).map((a) => (
              <div className="alert-card" key={a.id} style={{ marginBottom: 12 }}>
                <div className="count">{a.reports} reports</div>
                <p style={{ fontWeight: 700 }}>linked by shared details: likely one group using several names.</p>
                <ul className="entity-list">
                  {a.names.slice(0, 6).map((n) => <li key={n}>{n}</li>)}
                </ul>
                <p className="small muted" style={{ margin: 0 }}>
                  Linked through {Object.entries(a.links).map(([k, n]) => `${n} ${k.replace("_hash", "").replace("_", " ")}`).join(", ")} matches.
                </p>
              </div>
            ))}
            <div className="card" style={{ marginTop: 12 }}>
              <h3>Been through this?</h3>
              <p>Your story could stop the next person. Details are removed before anyone sees it.</p>
              <a className="btn" href="#/share">Share your story</a>
            </div>
            <div className="card" style={{ marginTop: 12 }}>
              <h3>Why there are no star ratings</h3>
              <p className="small">
                Scammers post fake good reviews. So we only take reports of what went wrong, never "this is
                legit" posts. And one report can never mark a licensed firm as a scam: copycats use real
                firms' names.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
