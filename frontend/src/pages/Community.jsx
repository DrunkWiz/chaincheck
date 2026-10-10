import { useEffect, useRef, useState } from "react";
import { api, OUTCOME_LABELS, SCAM_TYPE_LABELS } from "../api.js";

function ReportCard({ report }) {
  const [helped, setHelped] = useState(report.helped);
  const [clicked, setClicked] = useState(false);
  const [helpError, setHelpError] = useState("");
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? report.entities : report.entities.slice(0, 4);
  return (
    <article className="card report-card">
      <div className="meta">
        <span className="tag">{SCAM_TYPE_LABELS[report.scam_type] || report.scam_type}</span>
        <span className="tag">{OUTCOME_LABELS[report.outcome] || report.outcome}</span>
        {report.verdict === "STOP" && <span className="tag" style={{ background: "#FBECEB", color: "#A3241A" }}>✕ Checker said STOP</span>}
        {report.synthetic && <span className="tag synthetic">SYNTHETIC demo report</span>}
      </div>
      <p className={`story${expanded ? "" : " clamped"}`}>{report.story}</p>
      {report.story.length > 220 && (
        <button type="button" className="link-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? "Show less" : "Read more"}
        </button>
      )}
      {report.signals.length > 0 && (
        <p className="small"><strong>Signals:</strong> {report.signals.join(" · ")}</p>
      )}
      {report.entities.length > 0 && (
        <>
          <p className="small" style={{ margin: 0 }}><strong>Linked details</strong></p>
          <ul className="entity-list">
            {shown.map((e) => <li key={`${e.kind}-${e.display}`}>{e.display}</li>)}
            {shown.length < report.entities.length && <li className="muted">+{report.entities.length - shown.length} more</li>}
          </ul>
        </>
      )}
      {report.network_size > 1 && (
        <p className="small" style={{ color: "#A3241A", fontWeight: 700 }}>
          Linked to {report.network_size - 1} other {report.network_size === 2 ? "report" : "reports"} by shared details.
        </p>
      )}
      <button type="button" className="btn quiet" disabled={clicked}
        onClick={async () => {
          setClicked(true); setHelpError("");
          try { await api.helped(report.id); setHelped(n => n + 1); }
          catch (e) { setClicked(false); setHelpError(e.message); }
        }}>
        {clicked ? "Thank you" : "This helped me"} {helped > 0 ? `(${helped})` : ""}
      </button>
      {helpError && <p className="error" role="alert">{helpError}</p>}
    </article>
  );
}

export default function Community({ meta }) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState("recent");
  const requestId = useRef(0);
  async function load(q = query, t = type) {
    const id = ++requestId.current;
    setError(""); setLoading(true); setData(null);
    try { const next = await api.reports(q, t); if (id === requestId.current) setData(next); }
    catch (e) { if (id === requestId.current) setError(e.message); }
    finally { if (id === requestId.current) setLoading(false); }
  }

  useEffect(() => { load("", ""); return () => { requestId.current += 1; }; }, []);

  return (
    <section>
      <div className="wrap wide">
        <p className="eyebrow">Community reports</p>
        <h1>What happened to others</h1>
        <p className="muted">
          {meta?.demo ? "Explore invented reports that demonstrate how shared details link scam patterns." : "Explore reviewed reports of what went wrong, with personal details removed."} Search for a website, app, company or wallet you've been sent.
        </p>
        <form className="btn-row" role="search" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <label className="sr-only" htmlFor="search">Search reports</label>
          <input id="search" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. novaapex.example or a wallet address" style={{ flex: "1 1 260px" }} />
          <button className="btn">Search</button>
        </form>
        <div className="filters filters-chips" role="group" aria-label="Filter by scam type">
          <button type="button" className="chip" aria-pressed={type === ""} onClick={() => { setType(""); load(query, ""); }}>All</button>
          {Object.entries(SCAM_TYPE_LABELS).map(([k, l]) => (
            <button key={k} type="button" className="chip" aria-pressed={type === k}
              onClick={() => { setType(k); load(query, k); }}>{l}</button>
          ))}
        </div>
        <div className="filters-select">
          <label className="field" htmlFor="type-filter">Type of scam</label>
          <select id="type-filter" value={type} onChange={(e) => { setType(e.target.value); load(query, e.target.value); }}>
            <option value="">All types</option>
            {Object.entries(SCAM_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        {error && <p className="error" role="alert">{error}</p>}

        <div className="community-toolbar"><p role="status">{loading ? "Looking for reports…" : data ? `${data.reports.length} reports found` : "Reports unavailable"}</p><label className="sr-only" htmlFor="report-sort">Sort reports</label><select id="report-sort" value={sort} onChange={e => setSort(e.target.value)}><option value="recent">Newest first</option><option value="helpful">Most helpful</option><option value="linked">Most connected</option></select></div>
        <div className="community-layout">
          <aside className="alerts-area" aria-labelledby="alerts-heading">
            <h2 id="alerts-heading" className="h3">Network alerts</h2>
            {data?.alerts.length === 0 && <p className="small">No linked groups yet.</p>}
            {data?.alerts.slice(0, 3).map((a) => (
              <div className="alert-card" key={a.id}>
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
          </aside>
          <div className="list-area">
            {data && data.reports.length === 0 && <div className="empty-state"><h3>No matching reports</h3><p>Try a company name or fewer search terms. An empty result does not clear an offer.</p><button className="btn secondary" onClick={() => { setQuery(""); setType(""); load("", ""); }}>Clear filters</button></div>}
            {(data ? [...data.reports].sort((a,b) => sort === "helpful" ? b.helped - a.helped : sort === "linked" ? b.network_size - a.network_size : 0) : []).map((r) => <ReportCard key={r.id} report={r} />)}
          </div>
          <aside className="extras-area">
            <div className="card">
              <h3>Been through this?</h3>
              <p>Your story could stop the next person. Details are removed before anyone sees it.</p>
              <a className="btn" href="#/share">Share your story</a>
            </div>
            <div className="card">
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
