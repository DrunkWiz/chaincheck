export default function Stage({ stage }) {
  if (!stage) return null;
  return (
    <div className="panel">
      <h2>Where you are in the scam playbook</h2>
      <p>
        <strong>Stage {stage.number} of 7: {stage.name}.</strong>
      </p>
      <ol className="stage-track" aria-label="Scam playbook stages">
        {stage.stages.map((s) => (
          <li key={s.number} data-n={s.number}
            className={s.number === stage.number ? "current" : s.number < stage.number ? "done" : ""}
            aria-current={s.number === stage.number ? "step" : undefined}>
            {s.name}
          </li>
        ))}
      </ol>
      {stage.evidence.length > 0 && (
        <>
          <p className="small muted">What told us:</p>
          {stage.evidence.map((q) => <blockquote key={q}>{q}</blockquote>)}
        </>
      )}
      <div className="next-move">
        <strong>What they'll likely ask next:</strong> {stage.next_move}
      </div>
    </div>
  );
}
