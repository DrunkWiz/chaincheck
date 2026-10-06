"""One offer in, one result out (docs/BUILD_BRIEF.md §5).

extract (model + code) -> follow-up answers -> checks -> verdict -> explain.
The model only contributes entities and amber concerns. If every model
provider fails, the check still runs on code-side extraction alone and the
result says so.
"""

from dataclasses import dataclass, field
from datetime import date

from backend import code_extract, followups, normalize, playbook, reality, schema, snapshots, verdict
from backend.checks import Context, domain, mas, network, payment, people, returns
from backend.extract import cached_extract
from backend.flags import AMBER, RED
from backend.providers.base import ProviderError
from backend.redact import for_model, scrub_display


@dataclass
class Result:
    verdict: str
    headline: str
    summary: str
    counts: dict
    flags: list
    chain: list
    stage: dict
    reality: dict
    questions: list
    next_steps: list
    degraded: bool
    data: dict
    entities: dict = field(repr=False, default_factory=dict)

    @property
    def incomplete(self):
        return bool(self.questions)

    def to_dict(self):
        return {
            "verdict": self.verdict, "headline": self.headline, "summary": self.summary,
            "counts": self.counts, "flags": [f.to_dict() for f in self.flags], "chain": self.chain,
            "stage": self.stage, "reality": self.reality, "questions": self.questions,
            "incomplete": self.incomplete, "next_steps": self.next_steps, "degraded": self.degraded,
            "data": self.data, "evidence_summary": evidence_summary(self),
            "scamshield_url": "https://www.scamshield.gov.sg/",
        }


def make_context(today=None, rdap=None, network_lookup=None, fid=None, ial=None, secret=None):
    return Context(
        fid=fid or snapshots.load_latest("fid"),
        ial=ial or snapshots.load_latest("ial"),
        today=today or date.today(),
        rdap=rdap or domain.rdap_lookup,
        network=network_lookup,
        secret=secret,
    )


def analyze(offer_text, provider, ctx=None, answers=None):
    ctx = ctx or make_context()
    text = (offer_text or "").strip()
    degraded = provider is None

    code_entities, injection = code_extract.extract(text, ctx.fid.firms + ctx.ial.firms)
    model_entities = schema.empty_entities()
    if provider is not None and text:
        try:
            model_entities = cached_extract(for_model(text), provider).entities
        except ProviderError:
            degraded = True

    entities = code_extract.merge(model_entities, code_entities)
    answers = followups.clean_answers(answers or {})
    followups.apply(entities, answers)

    flags = run_checks(entities, injection, ctx)
    decided = verdict.decide(flags)
    is_stop = decided["verdict"] == verdict.STOP

    return Result(
        verdict=decided["verdict"], headline=decided["headline"], summary=decided["summary"],
        counts=decided["counts"], flags=[_scrub(f) for f in flags],
        chain=chain_map(entities, flags),
        stage=_scrub_stage(playbook.stage(entities)) if is_stop else None,
        reality=reality.reality_check(entities),
        questions=followups.questions_for(entities, answers),
        next_steps=decided["next_steps"], degraded=degraded,
        data={"fid": ctx.fid.label, "ial": ctx.ial.label, "demo": ctx.fid.demo or ctx.ial.demo,
              "checked_on": ctx.today.isoformat()},
        entities=entities,
    )


def run_checks(entities, injection, ctx):
    flags = []
    flags += mas.check(entities, ctx)          # first: fills on-record domains and copycats
    flags += domain.check(entities, ctx)
    flags += returns.check(entities, ctx)
    flags += payment.check_fees(entities, ctx)
    flags += payment.check_payment(entities, ctx)
    flags += payment.check_apps(entities, ctx)
    flags += payment.check_lockout(entities, ctx)
    flags += payment.check_recovery(entities, ctx)
    flags += people.check_people(entities, ctx)
    flags += people.check_injection(injection)
    flags += network.check(entities, ctx)
    flags += people.check_concerns(entities, ctx)
    # Reds first, stable within level.
    return sorted(flags, key=lambda f: 0 if f.level == RED else 1)


def _scrub(flag):
    from dataclasses import replace
    return replace(flag, title=scrub_display(flag.title), detail=scrub_display(flag.detail),
                   entity=scrub_display(flag.entity))


def _scrub_stage(stage):
    if stage:
        stage["evidence"] = [scrub_display(q) for q in stage["evidence"]]
    return stage


# --- Chain map ------------------------------------------------------------------

KIND_LABELS = {
    "person": "Person", "company": "Company", "app": "App", "domain": "Website",
    "email": "Email", "phone": "Phone", "wallet": "Crypto wallet", "account": "Bank account",
    "returns": "Promised returns", "fees": "Fees", "payment": "Payment",
}


def chain_map(entities, flags):
    nodes = []

    def add(kind, display):
        if not any(n["kind"] == kind and n["label"] == display for n in nodes):
            nodes.append({"kind": kind, "kind_label": KIND_LABELS[kind], "label": display})

    for p in entities["people"]:
        add("person", p["name"])
    for c in entities["companies"]:
        add("company", c)
    for a in entities["apps"]:
        add("app", a["name"])
    for d in entities["domains"]:
        add("domain", normalize.defang(normalize.domain(d)))
    for e in entities["emails"]:
        add("email", normalize.defang(e))
    if entities["phones"]:
        n = len(entities["phones"])
        add("phone", "1 phone number (hidden)" if n == 1 else f"{n} phone numbers (hidden)")
    for w in entities["wallets"]:
        add("wallet", normalize.short_wallet(w))
    if entities["accounts"]:
        add("account", "Bank account (hidden)")
    for flag in flags:
        if flag.entity_kind in ("returns", "fees", "payment"):
            add(flag.entity_kind, flag.entity)

    for node in nodes:
        mine = [f for f in flags if _belongs(f, node)]
        node["status"] = RED if any(f.level == RED for f in mine) else AMBER if mine else "unflagged"
        node["status_text"] = {"red": "Red flag", "amber": "Couldn't verify", "unflagged": "No flag found"}[node["status"]]
        node["flags"] = [scrub_display(f.title) for f in mine]
    return nodes


def _belongs(flag, node):
    if flag.entity_kind != node["kind"]:
        return False
    if node["kind"] in ("phone", "account"):
        return True
    return flag.entity == node["label"]


def evidence_summary(result):
    lines = [
        f"ChainCheck result ({result.data['checked_on']}): {result.headline}",
        result.summary,
        "",
    ]
    for f in result.flags:
        marker = "RED" if f.level == RED else "AMBER"
        lines.append(f"[{marker}] {f.title}")
        lines.append(f"    {f.detail}")
        lines.append(f"    Source: {f.source}")
    if result.stage:
        lines += ["", f"Scam playbook stage {result.stage['number']} of 7: {result.stage['name']}.",
                  f"What they'll likely ask next: {result.stage['next_move']}"]
    lines += ["", "ChainCheck can't catch every scam and never confirms an offer is safe.",
              "Report scams: https://www.scamshield.gov.sg/"]
    if result.data.get("demo"):
        lines.append("Note: this check used DEMO data with invented firms, not real MAS lists.")
    return "\n".join(lines)
