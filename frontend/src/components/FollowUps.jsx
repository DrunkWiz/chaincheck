import { useState } from "react";

export default function FollowUps({ questions, onAnswer, busy }) {
  const [company, setCompany] = useState("");
  if (!questions?.length) return null;
  return (
    <div className="panel followup-panel">
      <h2>A few questions to finish the check</h2>
      <p className="muted small">The offer didn't say. Your answers are only used for this check.</p>
      {questions.map((q) => (
        <fieldset key={q.id} style={{ border: 0, padding: 0, margin: "0 0 18px" }}>
          <legend style={{ fontWeight: 700, marginBottom: 8 }}>{q.text}</legend>
          {q.choices ? (
            <div className="choice-grid">
              {q.choices.map((c) => (
                <button key={c.value} type="button" className="btn quiet" disabled={busy}
                  onClick={() => onAnswer(q.id, c.value)}>
                  {c.label}
                </button>
              ))}
            </div>
          ) : (
            <form className="btn-row" onSubmit={(e) => { e.preventDefault(); if (company.trim()) onAnswer(q.id, company.trim()); }}>
              <label className="sr-only" htmlFor={`q-${q.id}`}>{q.text}</label>
              <input id={`q-${q.id}`} type="text" value={company} maxLength={120}
                onChange={(e) => setCompany(e.target.value)} style={{ flex: "1 1 220px" }} />
              <button className="btn" disabled={busy || !company.trim()}>Check this name</button>
            </form>
          )}
        </fieldset>
      ))}
    </div>
  );
}
