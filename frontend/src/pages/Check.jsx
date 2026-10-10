import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { readScreenshots } from "../ocr.js";
import { EXAMPLES } from "../examples.js";
import Icon from "../components/Icon.jsx";
import ReturnExplorer from "../components/ReturnExplorer.jsx";
import Results from "../components/Results.jsx";

const scrollBehavior = () =>
  (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");

const MAX_FILES = 4;
const MAX_BYTES = 10_000_000;
const TYPES = ["image/png", "image/jpeg", "image/webp"];

const GUIDED_PAY = [
  ["bank_transfer", "Bank transfer"], ["paynow", "PayNow"], ["cash_handover", "Cash, handed to someone"],
  ["gold", "Gold"], ["crypto", "Crypto"], ["not_asked", "They haven't asked yet"],
];
const PERIODS = [["day", "a day"], ["week", "a week"], ["month", "a month"], ["year", "a year"]];

function GuidedForm({ onSubmit, busy }) {
  const [company, setCompany] = useState("");
  const [percent, setPercent] = useState("");
  const [period, setPeriod] = useState("month");
  const [pay, setPay] = useState("");

  function submit(e) {
    e.preventDefault();
    const parts = [];
    if (company.trim()) parts.push(`The company or app is ${company.trim()}.`);
    if (percent) parts.push(`They promised ${percent}% ${PERIODS.find((p) => p[0] === period)[1]}.`);
    const answers = {};
    if (pay) answers.payment = pay;
    if (company.trim()) answers.company = company.trim();
    onSubmit(parts.join(" ") || "Someone offered me an investment.", answers);
  }

  return (
    <form onSubmit={submit}>
      <div style={{ marginBottom: 16 }}>
        <label className="field" htmlFor="g-company">1. What's the name of the company or app?</label>
        <input id="g-company" type="text" value={company} onChange={(e) => setCompany(e.target.value)} maxLength={120} />
      </div>
      <div style={{ marginBottom: 16 }}>
        <label className="field" htmlFor="g-percent">2. How much did they say you'd earn?</label>
        <div className="btn-row">
          <input id="g-percent" type="number" min="0" step="0.1" inputMode="decimal" value={percent}
            onChange={(e) => setPercent(e.target.value)} style={{ flex: "1 1 120px" }} aria-describedby="g-pct-help" />
          <label className="sr-only" htmlFor="g-period">per</label>
          <select id="g-period" value={period} onChange={(e) => setPeriod(e.target.value)} style={{ flex: "1 1 140px" }}>
            {PERIODS.map(([v, l]) => <option key={v} value={v}>% {l}</option>)}
          </select>
        </div>
        <p id="g-pct-help" className="small muted">Leave it empty if they didn't say.</p>
      </div>
      <fieldset style={{ border: 0, padding: 0, margin: "0 0 16px" }}>
        <legend className="field" style={{ fontWeight: 700, marginBottom: 6 }}>3. How do they want you to pay?</legend>
        <div className="choice-grid">
          {GUIDED_PAY.map(([v, l]) => (
            <label key={v} className="choice">
              <input type="radio" name="g-pay" value={v} checked={pay === v} onChange={() => setPay(v)} /> {l}
            </label>
          ))}
        </div>
      </fieldset>
      <button className="btn" disabled={busy}>{busy ? "Checking…" : "Check this offer"}</button>
    </form>
  );
}

export default function Check({ meta }) {
  const [mode, setMode] = useState("paste");
  const [text, setText] = useState("");
  const [reading, setReading] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [example, setExample] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const resultRef = useRef(null);
  const inputRef = useRef(null);
  const lastRequest = useRef(null);
  const sequence = useRef(0);
  useEffect(() => () => { sequence.current += 1; }, []);
  useEffect(() => {
    if (!busy) return;
    setElapsed(0);
    const timer = setInterval(() => setElapsed(n => n + 1), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  function edit(value) { setText(value); setResult(null); setError(""); setExample(null); }
  function useExample(ex) { edit(ex.text); setExample(ex.id); setMode("paste"); }
  async function run(payload) {
    const id = ++sequence.current;
    setBusy(true); setError(""); setResult(null);
    try {
      const data = await api.analyze(payload);
      if (id !== sequence.current) return;
      lastRequest.current = payload;
      setResult(data);
      setTimeout(() => { resultRef.current?.scrollIntoView({ behavior: scrollBehavior(), block: "start" }); resultRef.current?.focus({ preventScroll: true }); }, 60);
    } catch (e) { if (id === sequence.current) setError(e.message); }
    finally { if (id === sequence.current) setBusy(false); }
  }
  function onSubmit(e) {
    e.preventDefault();
    if (!text.trim()) { setError("Paste an offer, add a screenshot, or choose an example to get started."); inputRef.current?.focus(); return; }
    setAnswers({}); run({ text, answers: {} });
  }
  function onAnswer(id, value) {
    const next = { ...answers, [id]: value };
    setAnswers(next); run({ ...lastRequest.current, answers: next });
  }
  async function onFiles(files) {
    if (busy || reading) return;
    const picked = Array.from(files || []);
    if (!picked.length) return;
    if (picked.length > MAX_FILES) { setError("Choose up to 4 screenshots at a time."); return; }
    if (picked.some(f => !TYPES.includes(f.type) || f.size > MAX_BYTES)) { setError("Use PNG, JPEG or WebP screenshots, each under 10 MB."); return; }
    setError(""); setResult(null);
    setReading({ index: 0, total: picked.length, stage: "loading", percent: null });
    try {
      const texts = await readScreenshots(picked, setReading);
      const found = texts.map((t, i) => t ? `[Screenshot ${i + 1}]\n${t}` : "").filter(Boolean);
      if (!found.length) { setError("No text found. Try a clearer screenshot or paste the message."); return; }
      setText(current => [current.trim(), ...found].filter(Boolean).join("\n\n").slice(0, 20000));
      setMode("paste"); setExample(null);
      if (found.length < texts.length) setError("Some screenshots had no readable text. Review the text added below.");
    } catch { setError("The screenshot reader couldn't load. Try again or paste the message instead."); }
    finally { setReading(null); }
  }
  const locked = busy || !!reading;
  return <>
    <section className="check-home">
      <div className="wrap wide">
        <div className="workspace-heading"><span className="section-kicker"><span className="live-dot"/> YOUR INVESTMENT SECOND OPINION</span><span className="region-label">Made for Singapore · SG</span></div>
        <div className="intro-row"><div><h1>Before you invest,<br/><span>connect the dots.</span></h1><p className="intro-copy">A convincing story isn’t the whole story. Check the offer,<br className="desktop-break"/> uncover the warning signs, and see what could come next.</p></div><div className="intro-stamp"><Icon size={34}/><div><strong>Pause. Check. Protect.</strong><span>A little doubt is a good place to start.</span></div></div></div>
        <div className="check-layout">
          <div className="checker">
            <div className="checker-heading"><div className="number-icon">01</div><div><h2>Let’s look at the offer</h2><p>Start with what they sent you.</p></div><Icon name="search" size={26}/></div>
            <div className="mode-switch" role="group" aria-label="How do you want to check?">
              {[["paste", "text", "Paste text"], ["upload", "upload", "Screenshots"], ["guided", "book", "Guide me"]].map(([key, icon, label]) => <button key={key} type="button" className="chip" disabled={locked} aria-pressed={mode === key} onClick={() => { setMode(key); setError(""); }}><Icon name={icon} size={19}/>{label}</button>)}
            </div>
            {mode === "guided" ? <GuidedForm busy={locked} onSubmit={(t,a) => { setAnswers(a); run({ text:t, answers:a }); }}/> : <form onSubmit={onSubmit}>
              {mode === "upload" && <div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); onFiles(e.dataTransfer.files); }}><Icon name="upload" size={36}/><h3>Drop the conversation here</h3><p>Up to 4 images · PNG, JPG or WebP · 10 MB each</p><label className="btn secondary upload-control">Choose screenshots<input aria-label="Choose screenshots" type="file" accept="image/png,image/jpeg,image/webp" multiple disabled={locked} onChange={e => { onFiles(e.target.files); e.target.value=""; }}/></label><p className="small muted">Images stay on your device. Review the extracted text before checking.</p></div>}
              {mode === "paste" && <><div className="field-top"><label className="field" htmlFor="offer">The message, pitch or promise</label>{text && <button type="button" className="text-action" disabled={locked} onClick={() => edit("")}>Clear</button>}</div><div className="offer-box"><textarea ref={inputRef} id="offer" value={text} disabled={locked} onChange={e => edit(e.target.value)} maxLength={20000} placeholder={'“Join our private investment group. Earn 2% every day with our AI trading platform…”\n\nPaste the full message here. Names, websites and payment details help us connect the dots.'}/><div className="textarea-meta"><span><Icon name="lock" size={14}/> Not saved by ChainCheck</span><span>{text.length.toLocaleString()} / 20,000</span></div></div><button className="btn analyze-button" disabled={locked}>{busy ? <><span className="spinner"/> Checking the offer…</> : <>Check this offer <Icon name="arrow"/></>}</button></>}
            </form>}
            {reading && <p className="notice" role="status">{reading.stage === "loading" ? "Preparing the screenshot reader…" : `Reading screenshot ${reading.index + 1} of ${reading.total} · ${reading.percent ?? 0}%`}</p>}
            {busy && <p className="small muted" role="status">{elapsed < 8 ? "Reading the claims and checking for warning signs…" : "Still checking. External lookups can take a little longer…"} {elapsed}s</p>}
            {error && <p className="error" role="alert">{error}</p>}
            <details className="privacy-note"><summary><Icon name="lock" size={16}/> Your privacy, explained</summary><p>ChainCheck does not save your checks. Screenshots are read on your device. When available, Google’s Gemini reads the extracted text after phone numbers, emails, NRIC and account numbers are removed. Google may use that text to improve its products. Remove personal details before checking.</p></details>
          </div>
          <aside className="check-sidebar">
            <div className="insight-card"><span className="section-kicker">MORE THAN A YES OR NO</span><h2>Follow the whole chain.</h2><p>One convincing detail doesn’t make the rest add up.</p><ol className="check-capabilities">{[["search","Look beneath the claims","Firm records, contact details and website age."],["network","Spot the pattern","Payment requests, return promises and linked reports."],["shield","Know your next move","Understand the warning signs and what to do next."]].map(([icon,title,copy], i) => <li key={title}><span className="capability-icon"><Icon name={icon}/></span><div><strong>{title}</strong><p>{copy}</p></div><span className="step-index">0{i+1}</span></li>)}</ol><div className="insight-foot"><Icon name="check" size={17}/> Fixed rules decide. AI helps read.</div></div>
            <a className="help-card" href="https://www.scamshield.gov.sg/" target="_blank" rel="noreferrer"><Icon name="alert"/><span><strong>Already sent money?</strong><span>Find support with ScamShield</span></span><Icon name="arrow"/></a>
          </aside>
        </div>
        <div className="example-strip"><div><span className="section-kicker">TAKE IT FOR A TEST RUN</span><p>No message handy? Try an invented example.</p></div><div className="example-options">{EXAMPLES.map((ex, i) => <button key={ex.id} type="button" disabled={locked} aria-pressed={example === ex.id} onClick={() => useExample(ex)}><Icon name={["network","text","book"][i]}/><span>{["The copycat firm","The AI trading group","The broker promotion"][i]}<small>MOCK EXAMPLE</small></span><Icon name="arrow" size={18}/></button>)}</div></div>
        <div ref={resultRef} tabIndex={-1} className="result-anchor">{result && <><div className="report-heading"><div><p className="eyebrow">YOUR CHECK, EXPLAINED</p><h2>Here’s what we found.</h2></div><button className="btn quiet" onClick={() => { setResult(null); setText(""); setExample(null); setAnswers({}); setMode("paste"); window.scrollTo({top:0,behavior:scrollBehavior()}); }}>Start a new check <Icon name="arrow"/></button></div>{meta?.demo && <p className="notice">Demo report: firm records and community reports are invented. Do not use this as a real investment decision.</p>}<Results result={result} onAnswer={onAnswer} busy={busy}/></>}</div>
        {!result && <><ReturnExplorer/><div className="learn-banner"><div><p className="eyebrow">SAME PLAYBOOK. DIFFERENT NAMES.</p><h2>Learn to spot the next move.</h2><p>The friendly introduction. The small win. The bigger ask.<br/>Get familiar with the pattern before you’re part of it.</p><a className="btn" href="#/learn">Explore the scam playbook <Icon name="arrow"/></a></div><div className="playbook-preview" aria-label="Common scam sequence"><span>01 <b>The introduction</b></span><span>02 <b>The small win</b></span><span className="danger-step">03 <b>The bigger ask</b><Icon name="alert" size={18}/></span><span>04 <b>The withdrawal fee</b></span></div></div></>}
      </div>
    </section>
  </>;
}
