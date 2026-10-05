const MOVES = [
  {
    title: "The hook",
    bubbles: [["them", "📢 Famous investor reveals his secret AI trading method. Limited spots. Join our free group!"]],
    tell: "A public figure \"endorsing\" a secret method. Real public figures don't sell trading tips in ads.",
  },
  {
    title: "The group",
    bubbles: [
      ["them", "Welcome to VIP Group 18! Prof. shares picks at 9am daily."],
      ["them", "Member A: +$4,200 today, thank you Prof! 🙏"],
      ["them", "Member B: Withdrew $1,500, so easy!"],
    ],
    tell: "Everyone is winning, every day. Many \"members\" are the scammers themselves.",
  },
  {
    title: "The small win",
    bubbles: [
      ["me", "I deposited $500. Can I withdraw?"],
      ["them", "Of course! Done ✅ $120 sent to your bank."],
    ],
    tell: "Letting you withdraw a little is the bait. It's how they earn trust for the big deposit.",
  },
  {
    title: "The big ask and lockout",
    bubbles: [
      ["them", "Join our institutional programme: min $50,000. Our courier can collect cash."],
      ["me", "I want to withdraw my balance."],
      ["them", "Please pay the 15% withdrawal tax first."],
    ],
    tell: "Cash, gold or crypto, then a fee to get your own money out. Paying never releases it.",
  },
];

const ALSO = [
  ["Romance first", "Someone you met online slowly brings up an \"uncle\" or a platform that makes money."],
  ["\"Fund recovery\"", "After a loss, someone offers to get it back for a fee. It's usually the same people."],
  ["Copycat firms", "A real licensed firm's name, with a different phone number or website."],
  ["Deepfake videos", "Ads using real public figures' faces and voices. Assume any celebrity investment ad is fake."],
];

export default function Learn() {
  return (
    <section>
      <div className="wrap wide">
        <p className="eyebrow">Learn the signs</p>
        <h1>How investment scams work</h1>
        <p className="muted">
          They follow the same playbook. Once you know the moves, you can spot which one you're in.
        </p>

        <div className="card" style={{ marginBottom: 28 }}>
          <h2>Watch: how people who checked still got caught</h2>
          <p>
            CNA's investigation follows people who did their research: one Googled the contract, another ran
            background checks. Each verified one link, saw real money come back early, and trusted the rest.
          </p>
          <a className="btn" href="https://www.youtube.com/watch?v=b0Mn2ZAVEdo" target="_blank" rel="noreferrer">
            Watch on YouTube ↗
          </a>
          <p className="small muted" style={{ marginTop: 10 }}>
            The rule from the video: if you can't verify any part of it, stop.
          </p>
        </div>

        <h2>The four moves</h2>
        {MOVES.map((m, i) => (
          <div className="move card" key={m.title}>
            <div className="phone-mock" aria-label={`Mock chat: ${m.title}`}>
              <span className="tag mock mock-label">MOCK</span>
              {m.bubbles.map(([who, text], j) => (
                <div key={j} className={`bubble ${who === "me" ? "me" : ""}`}>{text}</div>
              ))}
            </div>
            <div>
              <h3>{i + 1}. {m.title}</h3>
              <div className="tell"><strong>The tell:</strong> {m.tell}</div>
            </div>
          </div>
        ))}

        <h2 style={{ marginTop: 32 }}>Also watch for</h2>
        <div className="grid">
          {ALSO.map(([t, d]) => <div className="card" key={t}><h3>{t}</h3><p>{d}</p></div>)}
        </div>

        <h2 style={{ marginTop: 32 }}>How a check works</h2>
        <ol className="steps">
          <li>An AI reads your text or screenshots and lists the names, links, numbers and payment requests. That's all it does.</li>
          <li>Fixed rules check each one: MAS's licence and alert lists, whether the contact details match the real firm, how old the website is, what the promised return works out to in a year, and how they want you to pay.</li>
          <li>Any red flag or claim we can't verify means STOP. The AI can add a warning but can never remove one.</li>
          <li>We never say an offer is safe. The best result is "No red flags found. Verify these yourself before you pay."</li>
        </ol>
        <a className="btn" href="#/">Check an offer</a>
      </div>
    </section>
  );
}
