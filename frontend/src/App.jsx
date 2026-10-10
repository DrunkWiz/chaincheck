import { useEffect, useState } from "react";
import { api } from "./api.js";
import Check from "./pages/Check.jsx";
import Community from "./pages/Community.jsx";
import Share from "./pages/Share.jsx";
import Learn from "./pages/Learn.jsx";
import Admin from "./pages/Admin.jsx";

const PAGES = {
  "": { title: "Check an offer", component: Check },
  community: { title: "Community reports", component: Community },
  share: { title: "Share your story", component: Share },
  learn: { title: "Learn the signs", component: Learn },
  admin: { title: "Review queue", component: Admin, hidden: true },
};

function currentRoute() {
  const route = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return route in PAGES ? route : "";
}

export default function App() {
  const [route, setRoute] = useState(currentRoute);
  const [meta, setMeta] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onHash = () => {
      setRoute(currentRoute());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    document.title = route ? `${PAGES[route].title} · ChainCheck` : "ChainCheck · Investment scam check for Singapore";
  }, [route]);

  const Page = PAGES[route].component;
  return (
    <>
      <a className="skip-link" href="#main" onClick={(e) => {
        e.preventDefault(); // "#main" would be read as a route by the hash router
        document.getElementById("main")?.focus();
      }}>Skip to content</a>
      {meta?.demo && (
        <div className="demo-banner" role="note">
          <div className="wrap wide">
            <details>
              <summary><span><strong>Demo data:</strong> invented firms and synthetic reports.</span></summary>
              <p>
                The MAS lists used here contain invented firms, and the community reports are synthetic.
                Don't rely on these results for a real decision.
              </p>
            </details>
          </div>
        </div>
      )}
      <header className="site-header">
        <div className="wrap wide header-row">
          <a className="brand" href="#/">
            <img src="/favicon.svg" alt="" width="32" height="32" /> ChainCheck
          </a>
          <button type="button" className="menu-button" aria-expanded={menuOpen} aria-controls="main-nav"
            onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? "Close" : "Menu"}
          </button>
          <nav id="main-nav" className={`nav${menuOpen ? " open" : ""}`} aria-label="Main">
            {Object.entries(PAGES)
              .filter(([, p]) => !p.hidden)
              .map(([key, p]) => (
                <a key={key} href={`#/${key}`} aria-current={route === key ? "page" : undefined}
                  onClick={() => setMenuOpen(false)}>
                  {p.title}
                </a>
              ))}
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        <Page meta={meta} />
      </main>
      <footer className="site-footer">
        <div className="wrap wide">
          <p>
            ChainCheck checks investment offers only. For suspicious calls, texts and links, use{" "}
            <a href="https://www.scamshield.gov.sg/" target="_blank" rel="noreferrer">ScamShield</a>.
            ChainCheck links to ScamShield; it doesn't send ScamShield any data.
          </p>
          <p>
            ChainCheck can't catch every scam and never tells you an offer is safe. MAS data shown is a
            dated snapshot, not live. {meta && <span>Using: {meta.fid}; {meta.ial}.</span>}
          </p>
          <p>All names, firms, numbers and screenshots in examples are invented.</p>
        </div>
      </footer>
    </>
  );
}
