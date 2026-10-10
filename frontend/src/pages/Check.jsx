import { useRef, useState } from "react";
import { api } from "../api.js";
import { readScreenshots } from "../ocr.js";
import { EXAMPLES } from "../examples.js";
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

export default function Check() {
  const [mode, setMode] = useState("paste");
  const [text, setText] = useState("");
  const [reading, setReading] = useState(null); // OCR progress, or null
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const resultRef = useRef(null);
  const lastRequest = useRef(null);

  async function run(payload) {
    setBusy(true);
    setError("");
    try {
      const data = await api.analyze(payload);
      lastRequest.current = payload;
      setResult(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: scrollBehavior(), block: "start" }), 50);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!text.trim()) {
      setError("Paste the offer or add a screenshot first.");
      return;
    }
    setAnswers({});
    run({ text, answers: {} });
  }

  function onAnswer(id, value) {
    const next = { ...answers, [id]: value };
    setAnswers(next);
    run({ ...lastRequest.current, answers: next });
  }

  async function onFiles(e) {
    const picked = [...e.target.files].slice(0, MAX_FILES);
    e.target.value = "";
    if (!picked.length) return;
    if (picked.some((f) => !TYPES.includes(f.type) || f.size > MAX_BYTES)) {
      setError("Screenshots must be PNG, JPEG or WebP, each under 10 MB.");
      return;
    }
    setError("");
    setReading({ index: 0, total: picked.length, stage: "loading", percent: null });
    try {
      const texts = await readScreenshots(picked, setReading);
      const found = texts.map((t, i) => (t ? `[From screenshot: ${picked[i].name}]\n${t}` : "")).filter(Boolean);
      if (!found.length) {
        setError("We couldn't find any text in that screenshot. Try a clearer one, or paste the text instead.");
        return;
      }
      setText((current) => [current.trim(), ...found].filter(Boolean).join("\n\n").slice(0, 20000));
      if (found.length < texts.length) {
        setError("We couldn't find text in some screenshots. The rest has been added.");
      }
    } catch {
      setError("Couldn't load the screenshot reader. Check your connection, or paste the text instead.");
    } finally {
      setReading(null);
    }
  }

  const readingText = reading && (reading.stage === "loading"
    ? `Getting the screenshot reader ready${reading.percent != null ? ` (${reading.percent}%)` : ""}… The first time takes a moment.`
    : `Reading screenshot ${reading.index + 1} of ${reading.total}… ${reading.percent}%`);

  return (
    <>
      <section className="hero">
        <div className="wrap wide hero-grid">
          <div className="hero-intro">
            <p className="eyebrow">Investment scam check for Singapore</p>
            <h1>Someone offered you an investment. Check it before you pay.</h1>
            <p className="muted hero-lede">
              Paste the messages or add screenshots. We check every claim we can, show where you are in the
              scam playbook, and tell you what they'll ask for next.
            </p>
            <ul className="hero-points">
              <li>Checks MAS licence lists, copycat contact details, website age and the maths on returns</li>
              <li>Fixed rules decide. The AI only reads the text, and can never mark anything safe</li>
              <li>Screenshots are read on your device and never uploaded</li>
            </ul>
          </div>

          <div className="checker">
            <div className="mode-switch" role="group" aria-label="How do you want to check?">
              <button type="button" className="chip" aria-pressed={mode === "paste"} onClick={() => setMode("paste")}>
                Paste or add screenshots
              </button>
              <button type="button" className="chip" aria-pressed={mode === "guided"} onClick={() => setMode("guided")}>
                Answer 3 questions
              </button>
            </div>

            {mode === "paste" ? (
              <form onSubmit={onSubmit}>
                <label className="field" htmlFor="offer">What did the offer say?</label>
                <textarea id="offer" value={text} onChange={(e) => setText(e.target.value)} maxLength={20000}
                  placeholder="Paste the chat, ad or message here. Include names, links, numbers and how they want you to pay." />
                <div className="checker-actions">
                  <button className="btn" disabled={busy || !!reading}>{busy ? "Checking…" : "Check this offer"}</button>
                  <label className={`btn quiet${reading ? " disabled" : ""}`} htmlFor="shots" aria-disabled={!!reading}>
                    Add screenshots
                    <input id="shots" type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={onFiles}
                      disabled={!!reading} />
                  </label>
                </div>
                <p role="status" aria-live="polite" className="small reading-status">{readingText}</p>
                <p className="small muted hint">
                  Screenshots (up to 4) are read on your device and never uploaded. Their text appears in the box,
                  so you can remove anything personal first.
                </p>
                <div className="examples">
                  <span className="small muted">Or try an invented example:</span>
                  {EXAMPLES.map((ex) => (
                    <button key={ex.id} type="button" className="chip" onClick={() => setText(ex.text)}>
                      {ex.label}
                    </button>
                  ))}
                </div>
              </form>
            ) : (
              <GuidedForm busy={busy} onSubmit={(t, a) => { setAnswers(a); run({ text: t, answers: a }); }} />
            )}
            {error && <p className="error" role="alert" style={{ marginTop: 14 }}>{error}</p>}
            <details className="privacy-note">
              <summary>We don't store what you check. How your data is handled</summary>
              <p>
                To read it, we send the text (never your screenshots) to Google's Gemini AI, with phone numbers,
                emails, NRIC and account numbers removed first. Google may use what it receives to improve its
                products. Only stories you choose to share are kept, after review.
              </p>
            </details>
          </div>
        </div>

        <div className="wrap">
          <div ref={resultRef} style={{ scrollMarginTop: 16 }}>
            {result && <Results result={result} onAnswer={onAnswer} busy={busy} />}
          </div>
        </div>
      </section>
      {!result && <Landing />}
    </>
  );
}

const SIGNS = [
  ["Returns that can't exist", "1% a day sounds small. It's over 3,600% a year."],
  ["A name that's almost right", "Copycats use real firms' names with their own phone numbers and sites."],
  ["An app from a link", "Scam platforms are installed from download links, not app stores."],
  ["Cash, gold or crypto", "Real firms never send a courier or ask for crypto to a wallet."],
  ["A small withdrawal that works", "They let you take a little out so you'll trust them with more."],
  ["Paying to get your money out", "A \"withdrawal tax\" or unlock fee is the last trick, not a real charge."],
];

function Landing() {
  return (
    <>
      <section>
        <div className="wrap wide">
          <div className="grid" style={{ alignItems: "start" }}>
            <div>
              <h2>What a check looks like</h2>
              <p>
                You get one clear answer, every link in the chain checked, and what the scammer will ask for next.
              </p>
              <p className="muted small">This example is invented and labelled MOCK.</p>
            </div>
            <div className="example-report" aria-label="Example report (MOCK)">
              <span className="tag mock">MOCK example</span>
              <div className="verdict stop">
                <h2 style={{ fontSize: "1.8rem" }}>STOP. Don't send money.</h2>
                <p className="summary">5 red flags, 2 claims we couldn't verify</p>
              </div>
              <div className="mini-links">
                <div className="mini-link"><span>Merlion Crest Capital</span><span>✕ Copycat</span></div>
                <div className="mini-link"><span>merlioncrest-capital[.]example</span><span>✕ 15 days old</span></div>
                <div className="mini-link"><span>32% a month</span><span>✕ 2,698% a year</span></div>
                <div className="mini-link"><span>Cash handover</span><span>✕ Red flag</span></div>
              </div>
              <div className="next-move" style={{ marginTop: 12 }}>
                <strong>Next they'll ask:</strong> a "withdrawal tax" before you can take money out.
              </div>
              <div className="btn-row" style={{ marginTop: 12 }}>
                <span className="btn stop" aria-hidden="true">Report on ScamShield</span>
                <span className="btn secondary" aria-hidden="true">Send to family</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <h2>How it works</h2>
          <div className="grid">
            <div className="card"><h3>1. You paste or upload</h3><p>The chat, the ad, the app screen. Screenshots are fine.</p></div>
            <div className="card"><h3>2. AI reads, code decides</h3><p>The AI only pulls out names, links, numbers and payment requests. Fixed rules do every check.</p></div>
            <div className="card"><h3>3. Every link is checked</h3><p>MAS licence lists, copycat contact details, website age, the maths on returns, how they want paying.</p></div>
            <div className="card"><h3>4. You see what's next</h3><p>Where you are in the scam playbook, and what they'll ask for next.</p></div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <h2>Use ScamShield and ChainCheck together</h2>
          <div className="together">
            <div className="card">
              <h3>ScamShield protects the inbox</h3>
              <p>It catches scam calls, texts and links that have been seen before. Use it for anything suspicious that reaches your phone.</p>
              <a href="https://www.scamshield.gov.sg/" target="_blank" rel="noreferrer">Go to ScamShield ↗</a>
            </div>
            <div className="card">
              <h3>ChainCheck protects the wallet</h3>
              <p>It's built for investment offers, which rename themselves every few weeks. It checks whether the claims add up, even the first time.</p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <div className="card">
            <div className="stat">41.4%</div>
            <p style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: 10 }}>
              of Singapore's scam losses in the first half of 2026 were investment scams: $169.8 million of
              $410.6 million.
            </p>
            <p className="small muted" style={{ margin: 0 }}>
              Source: Singapore Police Force, mid-year scam and cybercrime brief, August 2026. Share calculated
              by ChainCheck from the two totals.
            </p>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <h2>Six warning signs</h2>
          <ol className="signs">
            {SIGNS.map(([t, d]) => <li key={t}><strong>{t}.</strong> {d}</li>)}
          </ol>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <div className="card">
            <h2>Has this happened to you?</h2>
            <p>Read what others went through, and see when "different" platforms turn out to be one group.</p>
            <div className="btn-row">
              <a className="btn" href="#/community">Read community reports</a>
              <a className="btn secondary" href="#/share">Share your story</a>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap wide">
          <div className="band">
            <h2>Worried about a parent?</h2>
            <p>Check the offer together, then send them the result. It's evidence, not your opinion.</p>
            <a className="btn" href="#/learn">Learn the signs together</a>
          </div>
        </div>
      </section>
    </>
  );
}
