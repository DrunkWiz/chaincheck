import { useState } from "react";
import ChainMap from "./ChainMap.jsx";
import FollowUps from "./FollowUps.jsx";
import RealityCheck from "./RealityCheck.jsx";
import Stage from "./Stage.jsx";

function Flag({ flag }) {
  return (
    <article className={`flag ${flag.level}`}>
      <div className="level">{flag.level === "red" ? "✕ Red flag" : "! Couldn't verify"}</div>
      <h3>{flag.title}</h3>
      <p>{flag.detail}</p>
      <div className="source">Rule: {flag.rule} · Source: {flag.source}</div>
    </article>
  );
}

function Actions({ result }) {
  const [status, setStatus] = useState("");
  const [showEvidence, setShowEvidence] = useState(false);

  async function copy(text, done) {
    try {
      await navigator.clipboard.writeText(text);
      setStatus(done);
    } catch {
      setShowEvidence(true);
      setStatus("Copy didn't work here. Select the text below and copy it yourself.");
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

  return (
    <div className="panel">
      <h2>What to do now</h2>
      <ol className="steps">
        {result.next_steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
      <div className="actions">
        <a className="btn stop" href={result.scamshield_url} target="_blank" rel="noreferrer">
          Report on ScamShield ↗
        </a>
        <button type="button" className="btn secondary" onClick={sendToFamily}>Send to family</button>
        <button type="button" className="btn quiet" onClick={() => copy(result.evidence_summary, "Evidence summary copied.")}>
          Copy evidence summary
        </button>
      </div>
      <p role="status" aria-live="polite" className="small" style={{ marginTop: 10 }}>{status}</p>
      <details open={showEvidence} onToggle={(e) => setShowEvidence(e.currentTarget.open)}>
        <summary style={{ minHeight: 48, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 700 }}>
          Show the evidence summary
        </summary>
        <pre className="evidence">{result.evidence_summary}</pre>
      </details>
      <p className="small muted">
        ChainCheck links to ScamShield. It doesn't send ScamShield, the police or anyone else your details.
      </p>
    </div>
  );
}

export default function Results({ result, onAnswer, busy }) {
  const stop = result.verdict === "STOP";
  const reds = result.flags.filter((f) => f.level === "red");
  const ambers = result.flags.filter((f) => f.level === "amber");
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
      {result.transcript && (
        <details className="panel">
          <summary style={{ minHeight: 48, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 700 }}>
            Text we read from your screenshots
          </summary>
          <pre className="evidence">{result.transcript}</pre>
        </details>
      )}

      <FollowUps questions={result.questions} onAnswer={onAnswer} busy={busy} />

      {stop && <Stage stage={result.stage} />}
      <ChainMap chain={result.chain} />

      {reds.length > 0 && (
        <section style={{ padding: "0 0 8px" }}>
          <h2>{reds.length === 1 ? "1 red flag" : `${reds.length} red flags`}</h2>
          {reds.map((f, i) => <Flag key={`${f.rule}-${i}`} flag={f} />)}
        </section>
      )}
      {ambers.length > 0 && (
        <section style={{ padding: "8px 0" }}>
          <h2>{ambers.length === 1 ? "1 claim we couldn't verify" : `${ambers.length} claims we couldn't verify`}</h2>
          {ambers.map((f, i) => <Flag key={`${f.rule}-${i}`} flag={f} />)}
        </section>
      )}

      <RealityCheck reality={result.reality} />
      <Actions result={result} />

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
