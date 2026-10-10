import { useState } from "react";
import ChainMap from "./ChainMap.jsx";
import FollowUps from "./FollowUps.jsx";
import RealityCheck from "./RealityCheck.jsx";
import Stage from "./Stage.jsx";

const scrollBehavior = () =>
  (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");

const LEVEL_TEXT = { red: "✕ Red flag", amber: "! Couldn't verify" };

function Flag({ flag, id, open, onToggle }) {
  return (
    <details className={`flag ${flag.level}`} id={id} open={open}
      onToggle={(e) => onToggle(e.currentTarget.open)}>
      <summary>
        <span className="level">{LEVEL_TEXT[flag.level]}</span>
        <span className="flag-title">{flag.title}</span>
      </summary>
      <p>{flag.detail}</p>
      <p className="source">Rule: {flag.rule} · Source: {flag.source}</p>
    </details>
  );
}

function useShare(result) {
  const [status, setStatus] = useState("");
  const [showEvidence, setShowEvidence] = useState(false);

  async function copy(text, done) {
    try {
      await navigator.clipboard.writeText(text);
      setStatus(done);
    } catch {
      setShowEvidence(true);
      setStatus("Copy didn't work here. Open the evidence summary below and copy it yourself.");
    }
  }

  async function sendToFamily() {
    const text = `I checked an investment offer with ChainCheck.\n\n${result.evidence_summary}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "ChainCheck result", text });
        return;
      } catch {
        /* cancelled or unsupported: fall back to copying */
      }
    }
    copy(text, "Copied. Paste it into a message to your family.");
  }

  return { status, showEvidence, setShowEvidence, copy, sendToFamily };
}

function downloadReport(result) {
  const text = `CHAINCHECK — INVESTMENT OFFER CHECK\nChecked: ${result.data.checked_on}\nRecords: ${result.data.fid}; ${result.data.ial}\nRecords are dated snapshots and may be demo data. This is not a clearance to invest.\n\n${result.evidence_summary}\n\nFINDINGS\n${result.flags.map(f => `[${f.level.toUpperCase()}] ${f.title}\n${f.detail}\nRule: ${f.rule} | Source: ${f.source}`).join("\n\n")}\n\nNEXT STEPS\n${result.next_steps.map((s,i) => `${i+1}. ${s}`).join("\n")}\n\n${result.degraded ? "AI reader unavailable; fixed rules only.\n" : ""}ChainCheck cannot catch every scam and never establishes that an offer is safe.`;
  const url = URL.createObjectURL(new Blob([text], {type: "text/plain;charset=utf-8"}));
  const a = document.createElement("a"); a.href = url; a.download = "chaincheck-report.txt"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Summary({ result, share }) {
  const stop = result.verdict === "STOP";
  const top = result.flags.slice(0, 3); // reds come first
  const more = result.flags.length - top.length;
  return (
    <div className="panel summary-panel">
      {top.length > 0 && (
        <>
          <h2 className="h3">Why</h2>
          <ul className="reasons">
            {top.map((f, i) => (
              <li key={`${f.rule}-${i}`} className={f.level}>
                <span className="sr-only">{f.level === "red" ? "Red flag:" : "Couldn't verify:"}</span>
                <span aria-hidden="true" className="dot">{f.level === "red" ? "✕" : "!"}</span>
                {f.title}
              </li>
            ))}
          </ul>
          {more > 0 && (
            <button type="button" className="link-button"
              onClick={() => document.getElementById("all-flags")?.scrollIntoView({ behavior: scrollBehavior() })}>
              See all {result.flags.length} findings
            </button>
          )}
        </>
      )}
      {stop && result.stage && (
        <p className="next-move"><strong>Next they'll likely ask:</strong> {result.stage.next_move}</p>
      )}
      {!stop && (
        <ul className="steps">
          {result.next_steps.slice(0, 2).map((s) => <li key={s}>{s}</li>)}
        </ul>
      )}
      <div className="actions">
        {stop && (
          <a className="btn stop" href={result.scamshield_url} target="_blank" rel="noreferrer">
            Report on ScamShield ↗
          </a>
        )}
        <button type="button" className="btn secondary" onClick={share.sendToFamily}>Send to family</button>
        <button type="button" className="btn quiet"
          onClick={() => share.copy(result.evidence_summary, "Evidence summary copied.")}>
          Copy evidence
        </button>
      </div>
      <p role="status" aria-live="polite" className="small" style={{ margin: "8px 0 0" }}>{share.status}</p>
    </div>
  );
}

export default function Results({ result, onAnswer, busy }) {
  const stop = result.verdict === "STOP";
  const share = useShare(result);
  const [openFlags, setOpenFlags] = useState({});
  const allOpen = result.flags.length > 0 && result.flags.every((_, i) => openFlags[i]);

  function revealFlags(indices) {
    setOpenFlags((current) => ({ ...current, ...Object.fromEntries(indices.map((i) => [i, true])) }));
    // After React renders the opened details, bring the first one into view.
    setTimeout(() => document.getElementById(`flag-${indices[0]}`)?.scrollIntoView({ behavior: scrollBehavior(), block: "start" }), 50);
  }

  function toggleAll() {
    setOpenFlags(allOpen ? {} : Object.fromEntries(result.flags.map((_, i) => [i, true])));
  }

  const groups = [
    ["red", (n) => (n === 1 ? "1 red flag" : `${n} red flags`)],
    ["amber", (n) => (n === 1 ? "1 claim we couldn't verify" : `${n} claims we couldn't verify`)],
  ];

  return (
    <div aria-live="polite">
      <div className={`verdict ${stop ? "stop" : "clear"}`} role="status">
        <div className="verdict-icon" aria-hidden="true">{stop ? "✕" : "?"}</div>
        <h2>{result.headline}</h2>
        <p className="summary">{result.summary}</p>
      </div>

      {result.degraded && (
        <p className="notice">Our AI reader wasn't available, so this was checked with fixed rules only. It may miss things.</p>
      )}

      {!stop && <FollowUps questions={result.questions} onAnswer={onAnswer} busy={busy} />}
      <Summary result={result} share={share} />
      <div className="report-tools"><button className="btn secondary" onClick={() => downloadReport(result)}>Download report ↓</button><button className="btn quiet" onClick={() => window.print()}>Print report</button><span className="tag">Checked {result.data.checked_on}</span></div>
      {stop && <FollowUps questions={result.questions} onAnswer={onAnswer} busy={busy} />}

      {stop && <Stage stage={result.stage} />}
      <ChainMap chain={result.chain} flags={result.flags} onSelect={revealFlags} />

      {result.flags.length > 0 && (
        <section className="flags" id="all-flags" aria-labelledby="flags-heading">
          <div className="flags-head">
            <h2 id="flags-heading">All findings</h2>
            <button type="button" className="btn quiet" onClick={toggleAll}>
              {allOpen ? "Hide details" : "Show all details"}
            </button>
          </div>
          {groups.map(([level, label]) => {
            const items = result.flags.map((f, i) => [f, i]).filter(([f]) => f.level === level);
            if (!items.length) return null;
            return (
              <div key={level}>
                <h3>{label(items.length)}</h3>
                {items.map(([f, i]) => (
                  <Flag key={i} id={`flag-${i}`} flag={f} open={!!openFlags[i]}
                    onToggle={(open) => setOpenFlags((c) => (c[i] === open ? c : { ...c, [i]: open }))} />
                ))}
              </div>
            );
          })}
        </section>
      )}

      <RealityCheck reality={result.reality} />

      <div className="panel">
        <h2>What to do now</h2>
        <ol className="steps">
          {result.next_steps.map((s) => <li key={s}>{s}</li>)}
        </ol>
        <details open={share.showEvidence} onToggle={(e) => share.setShowEvidence(e.currentTarget.open)}>
          <summary>Show the evidence summary</summary>
          <pre className="evidence">{result.evidence_summary}</pre>
        </details>
        <p className="small muted">
          ChainCheck links to ScamShield. It doesn't send ScamShield, the police or anyone else your details.
        </p>
      </div>

      <details className="data-note">
        <summary>About this check</summary>
        <p>
          The AI only reads the text. Every check and the verdict come from fixed rules, and the AI can add
          a warning but never remove one. Checked on {result.data.checked_on} against: {result.data.fid};{" "}
          {result.data.ial}. These are dated snapshots, not live data.
        </p>
      </details>
    </div>
  );
}
