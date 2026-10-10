const COLORS = {
  red: { stroke: "#A3241A", fill: "#FBECEB", text: "#A3241A", mark: "✕" },
  amber: { stroke: "#B45309", fill: "#FDF3E6", text: "#7A4206", mark: "!" },
  unflagged: { stroke: "#9AA59F", fill: "#FFFFFF", text: "#46524D", mark: "–" },
};
const W = 360;
const H = 66;
const GAP = 16;

function clip(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** Every link in the offer with its status. Flagged nodes open their finding below. */
export default function ChainMap({ chain, flags = [], onSelect }) {
  if (!chain?.length) return null;
  const height = chain.length * (H + GAP) - GAP + 4;
  const flagIndexes = (node) => flags.map((f, i) => (node.flags.includes(f.title) ? i : -1)).filter((i) => i >= 0);
  return (
    <div className="panel chain">
      <h2>Chain map</h2>
      <p className="muted small">Every link in the offer and what we found. Tap a flagged link for the details.</p>
      <svg viewBox={`0 0 ${W} ${height}`} style={{ maxWidth: 520 }} role="list" aria-label="Chain map">
        {chain.map((node, i) => {
          const y = i * (H + GAP) + 2;
          const c = COLORS[node.status];
          const indexes = flagIndexes(node);
          const clickable = indexes.length > 0 && onSelect;
          const open = () => clickable && onSelect(indexes);
          return (
            <g key={`${node.kind}-${node.label}`} role="listitem"
              aria-label={`${node.kind_label}: ${node.label}. ${node.status_text}.${clickable ? " Show details." : ""}`}
              tabIndex={clickable ? 0 : undefined} className={clickable ? "chain-node clickable" : "chain-node"}
              onClick={open} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } }}>
              {i > 0 && <line x1={28} x2={28} y1={y - GAP} y2={y} stroke="#9AA59F" strokeWidth="3" strokeDasharray="4 4" />}
              <rect x="2" y={y} width={W - 4} height={H} rx="12" fill={c.fill} stroke={c.stroke} strokeWidth="2" />
              <rect x="2" y={y} width="10" height={H} rx="5" fill={c.stroke} />
              <text x="24" y={y + 25} fontSize="16" fill="#46524D" fontWeight="700">{node.kind_label}</text>
              <text x={W - 14} y={y + 25} fontSize="16" fill={c.text} fontWeight="700" textAnchor="end">
                {c.mark} {node.status_text}
              </text>
              <text x="24" y={y + 52} fontSize="19" fill="#16211D" fontWeight="700">{clip(node.label, 30)}</text>
              {clickable && <text x={W - 14} y={y + 52} fontSize="20" fill={c.text} textAnchor="end" aria-hidden="true">›</text>}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
