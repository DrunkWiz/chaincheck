// Home-page content the brief requires (§15): positioning next to ScamShield, the
// sourced 41.4% figure, the six warning signs and the family band.

const SIGNS = [
  ["Returns that can't exist", "1% a day sounds small. It's over 3,600% a year."],
  ["A name that's almost right", "Copycats use real firms' names with their own phone numbers and sites."],
  ["An app from a link", "Scam platforms are installed from download links, not app stores."],
  ["Cash, gold or crypto", "Real firms never send a courier or ask for crypto to a wallet."],
  ["A small withdrawal that works", "They let you take a little out so you'll trust them with more."],
  ["Paying to get your money out", "A \"withdrawal tax\" or unlock fee is the last trick, not a real charge."],
];

export default function HomeExtras() {
  return (
    <div className="home-extras">
      <section aria-labelledby="together-title">
        <h2 id="together-title">Use ScamShield and ChainCheck together</h2>
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
      </section>

      <section aria-label="Investment scam losses">
        <div className="card">
          <div className="stat">41.4%</div>
          <p className="stat-copy">
            of Singapore's scam losses in the first half of 2026 were investment scams: $169.8 million of
            $410.6 million.
          </p>
          <p className="small muted" style={{ margin: 0 }}>
            Source: Singapore Police Force, mid-year scam and cybercrime brief, August 2026. Share calculated
            by ChainCheck from the two totals.
          </p>
        </div>
      </section>

      <section aria-labelledby="signs-title">
        <h2 id="signs-title">Six warning signs</h2>
        <ol className="signs">
          {SIGNS.map(([t, d]) => <li key={t}><strong>{t}.</strong> {d}</li>)}
        </ol>
      </section>

      <section>
        <div className="band">
          <h2>Worried about a parent?</h2>
          <p>Check the offer together, then send them the result. It's evidence, not your opinion.</p>
          <div className="btn-row">
            <a className="btn" href="#/community">See what happened to others</a>
            <a className="btn" href="#/share">Share your story</a>
          </div>
        </div>
      </section>
    </div>
  );
}
