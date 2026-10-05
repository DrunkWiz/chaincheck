import { useRef, useState } from "react";
import { api, fileToBase64 } from "../api.js";
import { EXAMPLES } from "../examples.js";
import Results from "../components/Results.jsx";

const MAX_FILES = 4;
const MAX_BYTES = 4_000_000;
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
  const [files, setFiles] = useState([]);
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
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!text.trim() && !files.length) {
      setError("Paste the offer or add a screenshot first.");
      return;
    }
    const images = await Promise.all(files.map(async (f) => ({ mime: f.type, data: await fileToBase64(f) })));
    setAnswers({});
    run({ text, images, answers: {} });
  }

  function onAnswer(id, value) {
    const next = { ...answers, [id]: value };
    setAnswers(next);
    run({ ...lastRequest.current, answers: next });
  }

  function onFiles(e) {
    const picked = [...e.target.files];
    e.target.value = "";
    const bad = picked.find((f) => !TYPES.includes(f.type) || f.size > MAX_BYTES);
    if (bad) {
      setError("Screenshots must be PNG, JPEG or WebP, each under 4 MB.");
      return;
    }
    setError("");
    setFiles((current) => [...current, ...picked].slice(0, MAX_FILES));
  }

  return (
    <>
      <section className="hero">
        <div className="wrap">
          <p className="eyebrow">Investment scam check for Singapore</p>
          <h1>Someone offered you an investment. Check it before you pay.</h1>
          <p className="muted">
            Paste the messages or upload screenshots. We check every claim we can, show where you are in the
            scam playbook, and tell you what they'll ask for next.
          </p>

          <div className="checker">
            <div className="btn-row" role="tablist" aria-label="How to check" style={{ marginBottom: 14 }}>
              <button type="button" role="tab" aria-selected={mode === "paste"} className={`chip`}
                aria-pressed={mode === "paste"} onClick={() => setMode("paste")}>Paste or upload</button>
              <button type="button" role="tab" aria-selected={mode === "guided"} className="chip"
                aria-pressed={mode === "guided"} onClick={() => setMode("guided")}>Answer 3 questions</button>
            </div>

            {mode === "paste" ? (
              <form onSubmit={onSubmit}>
                <label className="field" htmlFor="offer">What did the offer say?</label>
                <textarea id="offer" value={text} onChange={(e) => setText(e.target.value)} maxLength={20000}
                  placeholder="Paste the chat, ad or message here. Include names, links, numbers and how they want you to pay." />
                <div className="upload">
                  <label className="btn quiet" htmlFor="shots">
                    Add screenshots
                    <input id="shots" type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={onFiles} />
                  </label>
                  <span className="small muted">Up to 4 images. We read the text out of them.</span>
                </div>
                {files.length > 0 && (
                  <div className="file-list" style={{ marginBottom: 12 }}>
                    {files.map((f, i) => (
                      <span className="file-pill" key={`${f.name}-${i}`}>
                        {f.name}
                        <button type="button" aria-label={`Remove ${f.name}`}
                          onClick={() => setFiles(files.filter((_, j) => j !== i))}>×</button>
                      </span>
                    ))}
                  </div>
                )}
                <button className="btn" disabled={busy}>{busy ? "Checking…" : "Check this offer"}</button>
                <div className="examples">
                  <span className="small muted">Try an invented example:</span>
                  {EXAMPLES.map((ex) => (
                    <button key={ex.id} type="button" className="btn quiet" onClick={() => { setText(ex.text); setFiles([]); }}>
                      {ex.label}
                    </button>
                  ))}
                </div>
              </form>
            ) : (
              <GuidedForm busy={busy} onSubmit={(t, a) => { setAnswers(a); run({ text: t, images: [], answers: a }); }} />
            )}
            {error && <p className="error" role="alert" style={{ marginTop: 14 }}>{error}</p>}
            <p className="small muted" style={{ marginTop: 14, marginBottom: 0 }}>
              We don't store what you check. Only stories you choose to share are kept, after review.
            </p>
          </div>

          <div ref={resultRef} style={{ scrollMarginTop: 90 }}>
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
