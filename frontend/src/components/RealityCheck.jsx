const W = 360;
const ROW = 58;
const LEFT = 8;
const BAR_W = W - LEFT - 8;

function width(percent, max) {
  // Log scale: 2,700% and 2.5% have to fit on one chart.
  return Math.max(4, (Math.log10(percent + 1) / Math.log10(max + 1)) * BAR_W);
}

export default function RealityCheck({ reality }) {
  if (!reality?.claims?.length) return null;
  const rows = [
    ...reality.claims.map((c) => ({ label: `Promised: ${c.claimed}`, value: c.annual_percent, text: `${c.annual_text} a year`, color: "#A3241A" })),
    { label: "ChainCheck red line", value: reality.red_line_percent, text: `${reality.red_line_percent}% a year`, color: "#16211D" },
    ...reality.benchmarks.map((b) => ({ label: b.label, value: b.annual_percent, text: `${b.annual_percent}% a year (${b.source})`, color: "#0F5A4D" })),
  ];
  const max = Math.max(...rows.map((r) => r.value), 100);
  const first = reality.claims[0];
  return (
    <div className="panel reality">
      <h2>Reality Check</h2>
      <p>
        <strong>{first.claimed}</strong> works out to <strong>{first.annual_text} a year</strong>, compounded.
        At that rate, $1,000 would become <strong>{first.thousand_becomes}</strong> in a year. This is the mathematical implication of the claim, not a prediction of actual returns.
      </p>
      <svg viewBox={`0 0 ${W} ${rows.length * ROW}`} style={{ maxWidth: 560 }} role="img"
        aria-label={rows.map((r) => `${r.label}: ${r.text}`).join("; ")}>
        {rows.map((r, i) => (
          <g key={r.label} transform={`translate(0 ${i * ROW})`}>
            <text x={LEFT} y="18" fontSize="15" fill="#16211D" fontWeight="700">{r.label}</text>
            <rect x={LEFT} y="26" width={width(r.value, max)} height="16" rx="4" fill={r.color} />
            <text x={Math.min(LEFT + width(r.value, max) + 6, W - 4)} y="39" fontSize="14" fill="#46524D"
              textAnchor={width(r.value, max) > BAR_W - 120 ? "end" : "start"}
              dx={width(r.value, max) > BAR_W - 120 ? -10 : 0}
              style={width(r.value, max) > BAR_W - 120 ? { fill: "#fff", fontWeight: 700 } : undefined}>
              {r.text}
            </text>
          </g>
        ))}
      </svg>
      <p className="small muted">Log scale, so the small bars stay visible. {reality.benchmarks_note}</p>
    </div>
  );
}
