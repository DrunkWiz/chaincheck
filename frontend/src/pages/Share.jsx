import { useState } from "react";
import { api, OUTCOME_LABELS, SCAM_TYPE_LABELS } from "../api.js";

const REMOVED_LABELS = {
  "[NAME]": "names", "[PHONE]": "phone numbers", "[NRIC]": "NRIC/FIN numbers",
  "[ACCOUNT]": "bank account numbers", "[EMAIL]": "email addresses",
};

export default function Share() {
  const [story, setStory] = useState("");
  const [outcome, setOutcome] = useState("");
  const [scamType, setScamType] = useState("");
  const [preview, setPreview] = useState(null);
  const [confirm, setConfirm] = useState({ redaction: false, truthful: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function makePreview(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setPreview(await api.preview(story));
      setConfirm({ redaction: false, truthful: false });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    setBusy(true);
    setError("");
    try {
      await api.submit({ story, outcome, scam_type: scamType, confirmations: confirm });
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <section>
        <div className="wrap">
          <h1>Thank you. Your story is in the review queue.</h1>
          <p>Someone will check it before it's published. You don't need to do anything else.</p>
          <p>If you've lost money, also report it on ScamShield and to the police, and call your bank.</p>
          <div className="btn-row">
            <a className="btn stop" href="https://www.scamshield.gov.sg/" target="_blank" rel="noreferrer">Report on ScamShield ↗</a>
            <a className="btn secondary" href="#/community">Read other reports</a>
          </div>
        </div>
      </section>
    );
  }

  const removed = preview ? Object.entries(preview.removed) : [];
  return (
    <section>
      <div className="wrap">
        <p className="eyebrow">Share your story</p>
        <h1>Tell others what happened</h1>
        <p className="muted">
          No account needed. We remove names, phone numbers, NRIC/FIN, bank account numbers and emails before
          anything is stored, and every story is reviewed before it's published.
        </p>
        <form onSubmit={makePreview} className="card">
          <label className="field" htmlFor="story">What happened?</label>
          <textarea id="story" value={story} maxLength={8000} onChange={(e) => { setStory(e.target.value); setPreview(null); }}
            placeholder="How they found you, the company or app name, websites, how they asked you to pay, what happened when you tried to withdraw." />

          <fieldset style={{ border: 0, padding: 0, margin: "16px 0" }}>
            <legend className="field" style={{ fontWeight: 700 }}>How did it end?</legend>
            <div className="choice-grid">
              {Object.entries(OUTCOME_LABELS).map(([k, l]) => (
                <label key={k} className="choice">
                  <input type="radio" name="outcome" value={k} checked={outcome === k} onChange={() => setOutcome(k)} /> {l}
                </label>
              ))}
            </div>
          </fieldset>
          <div style={{ marginBottom: 16 }}>
            <label className="field" htmlFor="type">What kind of scam was it?</label>
            <select id="type" value={scamType} onChange={(e) => setScamType(e.target.value)}>
              <option value="">Choose one</option>
              {Object.entries(SCAM_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </div>
          <button className="btn" disabled={busy || story.trim().length < 40}>
            {busy && !preview ? "Preparing…" : "Preview what will be shared"}
          </button>
          {story.trim().length > 0 && story.trim().length < 40 && (
            <p className="small muted">A few more sentences, please.</p>
          )}
        </form>

        {error && <p className="error" role="alert" style={{ marginTop: 14 }}>{error}</p>}

        {preview && (
          <div className="card" style={{ marginTop: 18 }}>
            <h2>Preview</h2>
            <p className="small muted">This is exactly what reviewers and readers will see.</p>
            <pre className="evidence">{preview.redacted}</pre>
            <p>
              {removed.length
                ? `Removed: ${removed.map(([k, n]) => `${n} ${REMOVED_LABELS[k] || k}`).join(", ")}.`
                : "We didn't find personal details to remove. Check the preview yourself."}
            </p>
            {preview.entities.length > 0 && (
              <>
                <p className="small" style={{ margin: 0 }}><strong>Details that will link your report to others:</strong></p>
                <ul className="entity-list">
                  {preview.entities.map((e) => <li key={`${e.kind}-${e.display}`}>{e.display}</li>)}
                </ul>
                <p className="small muted">Phone numbers and bank accounts are matched in coded form and never shown.</p>
              </>
            )}
            <label className="choice" style={{ marginBottom: 8 }}>
              <input type="checkbox" checked={confirm.redaction} onChange={(e) => setConfirm({ ...confirm, redaction: e.target.checked })} />
              I've read the preview and it has no personal details I want hidden.
            </label>
            <label className="choice" style={{ marginBottom: 14 }}>
              <input type="checkbox" checked={confirm.truthful} onChange={(e) => setConfirm({ ...confirm, truthful: e.target.checked })} />
              This happened to me or someone I know.
            </label>
            <button type="button" className="btn" onClick={send}
              disabled={busy || !confirm.redaction || !confirm.truthful || !outcome || !scamType}>
              {busy ? "Sending…" : "Send for review"}
            </button>
            {(!outcome || !scamType) && <p className="small muted">Choose how it ended and the type of scam above.</p>}
          </div>
        )}
      </div>
    </section>
  );
}
