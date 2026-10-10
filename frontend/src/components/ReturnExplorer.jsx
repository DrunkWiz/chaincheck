import { useState } from "react";

export function annualReturn(percent, period) {
  return Math.expm1(({ day: 365, week: 52, month: 12, year: 1 }[period] || 1) * Math.log1p(percent / 100)) * 100;
}

export default function ReturnExplorer() {
  const [rate, setRate] = useState("2");
  const [period, setPeriod] = useState("month");
  const valid = rate.trim() !== "" && Number.isFinite(Number(rate)) && Number(rate) >= 0 && Number(rate) <= 1000;
  const annual = valid ? annualReturn(Number(rate), period) : null;
  const format = value => value > 1e9 ? "over 1 billion" : value.toLocaleString("en-SG", { maximumFractionDigits: 1 });
  return <section className="return-explorer" aria-labelledby="returns-title">
    <div><p className="eyebrow">The numbers behind the promise</p><h2 id="returns-title">“Just 2%” can add up fast.</h2><p>Turn a daily, weekly or monthly promise into a yearly figure. Small numbers can hide a very big claim.</p><span className="small muted">Illustration only. Assumes every return is reinvested; excludes fees and losses.</span></div>
    <div className="calculator"><label className="field" htmlFor="explore-rate">They promised a return of</label><div className="calculator-inputs"><input id="explore-rate" type="number" min="0" max="1000" step="0.1" value={rate} onChange={e => setRate(e.target.value)}/><span>%</span><select aria-label="Return period" value={period} onChange={e => setPeriod(e.target.value)}><option value="day">per day</option><option value="week">per week</option><option value="month">per month</option><option value="year">per year</option></select></div><div className="calculator-output" aria-live="polite">{valid ? <><strong>{format(annual)}%</strong><span>compounded over one year</span><p>$1,000 would become <b>{annual > 1e10 ? "over $100 billion" : `$${format(1000 * (1 + annual / 100))}`}</b>.</p></> : <p>Enter a return between 0% and 1,000%.</p>}</div><p className="small muted">This calculation does not establish whether an offer is trustworthy.</p></div>
  </section>;
}
