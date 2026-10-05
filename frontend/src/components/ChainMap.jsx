const COLORS = {
  red: { stroke: "#A3241A", fill: "#FBECEB", text: "#A3241A", mark: "✕" },
  amber: { stroke: "#B45309", fill: "#FDF3E6", text: "#7A4206", mark: "!" },
  unflagged: { stroke: "#9AA59F", fill: "#FFFFFF", text: "#46524D", mark: "–" },
};
const W = 360;
const H = 78;
const GAP = 22;

function clip(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export default function ChainMap({ chain }) {
  if (!chain?.length) return null;
  const height = chain.length * (H + GAP) - GAP + 4;
  const summary = chain.map((n) => `${n.kind_label}: ${n.label}, ${n.status_text}`).join("; ");
  return (
    <div className="panel chain">
      <h2>Chain map</h2>
      <p className="muted small">Every link in the offer, and what we found on each.</p>
      <svg viewBox={`0 0 ${W} ${height}`} style={{ maxWidth: 480 }} role="img" aria-label={`Chain map. ${summary}`}>
        {chain.map((node, i) => {
          const y = i * (H + GAP) + 2;
          const c = COLORS[node.status];
          return (
            <g key={`${node.kind}-${node.label}`}>
              {i > 0 && <line x1={28} x2={28} y1={y - GAP} y2={y} stroke="#9AA59F" strokeWidth="3" strokeDasharray="4 4" />}
              <rect x="2" y={y} width={W - 4} height={H} rx="12" fill={c.fill} stroke={c.stroke} strokeWidth="2" />
              <rect x="2" y={y} width="10" height={H} rx="5" fill={c.stroke} />
              <text x="24" y={y + 24} fontSize="15" fill="#46524D" fontWeight="700">{node.kind_label}</text>
              <text x={W - 14} y={y + 24} fontSize="15" fill={c.text} fontWeight="700" textAnchor="end">
                {c.mark} {node.status_text}
              </text>
              <text x="24" y={y + 52} fontSize="18" fill="#16211D" fontWeight="700">{clip(node.label, 32)}</text>
              {node.flags[0] && node.flags[0] !== node.label && (
                <text x="24" y={y + 70} fontSize="13" fill={c.text}>{clip(node.flags[0], 48)}</text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
