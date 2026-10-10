import Icon from "./Icon.jsx";

/** Linked evidence uses native buttons so it works equally well by touch or keyboard. */
export default function ChainMap({ chain, flags = [], onSelect }) {
  if (!chain?.length) return null;
  return <div className="panel chain"><div className="chain-heading"><div><p className="eyebrow">THE OFFER, LINK BY LINK</p><h2>Connect the evidence</h2></div><Icon name="network" size={28}/></div><p className="muted small">Each detail tells part of the story. Choose a flagged link to see the evidence.</p><ul className="evidence-chain" aria-label="Chain map">{chain.map((node, i) => {
    const indexes = flags.map((f, j) => node.flags.includes(f.title) ? j : -1).filter(j => j >= 0);
    const clickable = indexes.length > 0 && !!onSelect;
    const content = <><span className="evidence-kind"><span>{String(i+1).padStart(2,"0")} / {node.kind_label}</span>{clickable && <Icon name="arrow" size={16}/>}</span><strong>{node.label}</strong><span className="evidence-status">{node.status === "red" ? "✕" : node.status === "amber" ? "!" : "–"} {node.status_text}</span></>;
    return <li key={`${node.kind}-${node.label}`} className={node.status}>{clickable ? <button onClick={() => onSelect(indexes)} aria-label={`${node.kind_label}: ${node.label}. ${node.status_text}. Show details.`}>{content}</button> : <div>{content}</div>}</li>;
  })}</ul></div>;
}
