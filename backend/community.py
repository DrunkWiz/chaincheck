"""Community reports and the scam network (docs/BUILD_BRIEF.md §10).

Every story runs through the checker so its entities are already extracted,
and is redacted before storage. Code then publishes it, or holds it in the
review queue when code or the AI screen gives a reason (backend/moderation.py).
Publishing a report recomputes the network: union-find over shared entities.
"""

import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from backend import config, moderation, normalize, redact
from backend.checks import network
from backend.pipeline import analyze

# Signals shown on report cards: rule ids that describe the scam, not people.
_SIGNAL_TITLES = {
    "copycat.contact_mismatch": "Copied a licensed firm's name",
    "mas.lookalike_name": "Name close to a licensed firm",
    "mas.not_licensed": "Firm not licensed by MAS",
    "mas.alert_list": "On MAS Investor Alert List",
    "domain.very_new": "Brand-new website",
    "domain.new": "Website under a year old",
    "returns.too_high": "Impossible returns",
    "returns.high": "Very high returns",
    "fees.withdrawal_tax": "Withdrawal \"tax\"",
    "fees.unlock_fee": "Fee to unlock account",
    "fees.withdrawal_fee": "Fee to withdraw",
    "payment.cash_handover": "Cash handover",
    "payment.gold": "Paid in gold",
    "payment.crypto_wallet": "Crypto to a wallet",
    "payment.crypto": "Crypto payment",
    "app.from_link": "App from a download link",
    "recovery.offer": "Fund recovery offer",
    "lockout.withdrawal_blocked": "Withdrawal blocked",
    "lockout.minimum_trading_commitment": "Trading target to withdraw",
    "lockout.account_frozen": "Account \"frozen\"",
    "person.claimed_title": "Unverifiable \"expert\"",
    "text.ai_instructions": "Instructions aimed at AI",
}


class ReportError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _check_story(story, provider, ctx):
    story = (story or "").strip()
    if len(story) < 40:
        raise ReportError("Please describe what happened in at least a few sentences.")
    if len(story) > config.MAX_REPORT_CHARS:
        raise ReportError(f"Please keep your story under {config.MAX_REPORT_CHARS} characters.")
    result = analyze(story, provider, ctx)
    names = [p["name"] for p in result.entities["people"]]
    redacted, counts = redact.redact(story, names)
    signals = sorted({_SIGNAL_TITLES[f.rule] for f in result.flags if f.rule in _SIGNAL_TITLES})
    return result, redacted, counts, signals


def preview(story, provider, ctx, secret=None):
    """What would be stored. Nothing is saved."""
    result, redacted, counts, signals = _check_story(story, provider, ctx)
    keys = _linkable(result.entities, ctx, secret)
    return {
        "redacted": redacted,
        "removed": counts,
        "verdict": result.verdict,
        "signals": signals,
        "entities": [{"kind": k, "display": d} for k, _, d in keys],
    }


def submit(db, story, outcome, scam_type, confirmations, provider, ctx, secret=None, synthetic=False,
           status=None, report_id=None):
    """Store a report and return its id. With no `status`, code decides: published, or held for a person."""
    if outcome not in config.OUTCOMES:
        raise ReportError("Choose how it ended.")
    if scam_type not in config.SCAM_TYPES:
        raise ReportError("Choose the type of scam.")
    if not synthetic and not (confirmations.get("redaction") and confirmations.get("truthful")):
        raise ReportError("Please confirm both statements before sending.")
    result, redacted, _, signals = _check_story(story, provider, ctx)
    linkable, licensed = _split_licensed(result.entities, ctx, secret)
    held = []
    if status is None:
        held = moderation.hold_reasons(
            redacted, {f.rule for f in result.flags}, [d for _, _, d in licensed],
            duplicate=bool(db.execute("SELECT 1 FROM reports WHERE story = ? LIMIT 1", (redacted,))),
            published_last_hour=_auto_published_since(db, datetime.now(timezone.utc) - timedelta(hours=1)),
            provider=provider)
        status = "pending" if held else "approved"
    report_id = report_id or secrets.token_hex(8)
    statements = [(
        "INSERT OR IGNORE INTO reports (id, story, outcome, scam_type, verdict, signals, status, synthetic, "
        "created_at, held_reasons, auto_published) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (report_id, redacted, outcome, scam_type, result.verdict, json.dumps(signals), status,
         int(synthetic), _now(), json.dumps(held), int(status == "approved" and not synthetic)),
    )]
    for kind, key, display in linkable:
        statements.append((
            "INSERT INTO entities (kind, value, display) VALUES (?, ?, ?) ON CONFLICT (kind, value) DO NOTHING",
            (kind, key, display)))
        statements.append((
            "INSERT OR IGNORE INTO report_entities (report_id, entity_id) "
            "SELECT ?, id FROM entities WHERE kind = ? AND value = ?",
            (report_id, kind, key)))
    db.batch(statements)
    if status == "approved":
        recompute_clusters(db)
    return report_id


def _split_licensed(entities, ctx, secret):
    """(keys that may link reports, keys that belong to a MAS-licensed firm's name, site or phone).
    Reports never link a licensed firm."""
    licensed = network.licensed_keys(ctx.fid)
    keys = network.entity_keys(entities, secret)
    licensed_phones = ({normalize.keyed_hash(p, secret) for f in ctx.fid.firms for p in f.phones}
                       if any(k == "phone_hash" for k, _, _ in keys) else set())
    linkable, firm = [], []
    for k, v, d in keys:
        is_licensed = (k, v) in licensed or (k == "phone_hash" and v in licensed_phones)
        (firm if is_licensed else linkable).append((k, v, "A licensed firm's phone number" if k == "phone_hash" else d))
    return linkable, firm


def _linkable(entities, ctx, secret):
    return _split_licensed(entities, ctx, secret)[0]


def _auto_published_since(db, since):
    rows = db.execute("SELECT COUNT(*) AS n FROM reports WHERE auto_published = 1 AND created_at >= ?",
                      (since.isoformat(timespec="seconds"),))
    return rows[0]["n"]


# --- Review queue -----------------------------------------------------------------

def pending(db):
    """Reports held for a person, with the reasons they were held. Moderators only."""
    rows = db.execute("SELECT * FROM reports WHERE status = 'pending' ORDER BY created_at")
    entities = _entities_for(db, [r["id"] for r in rows])
    return [{**_public(r, entities.get(r["id"], []), None), "held": json.loads(r["held_reasons"])}
            for r in rows]


def auto_published(db, limit=50):
    """Reports code published without a person, newest first, so a moderator can take one down."""
    rows = db.execute("SELECT * FROM reports WHERE status = 'approved' AND auto_published = 1 "
                      "ORDER BY created_at DESC LIMIT ?", (limit,))
    entities = _entities_for(db, [r["id"] for r in rows])
    return [_public(r, entities.get(r["id"], []), None) for r in rows]


def status_of(db, report_id):
    rows = db.execute("SELECT status FROM reports WHERE id = ?", (report_id,))
    return rows[0]["status"] if rows else None


def review(db, report_id, approve):
    rows = db.execute("SELECT status FROM reports WHERE id = ?", (report_id,))
    if not rows:
        raise ReportError("No such report.")
    db.execute("UPDATE reports SET status = ?, reviewed_at = ? WHERE id = ?",
               ("approved" if approve else "rejected", _now(), report_id))
    recompute_clusters(db)
    _index_cache.clear()


def mark_helped(db, report_id):
    db.execute("UPDATE reports SET helped = helped + 1 WHERE id = ? AND status = 'approved'", (report_id,))


# --- Network: union-find over shared entities ----------------------------------------

def recompute_clusters(db):
    links = db.execute(
        "SELECT re.report_id, re.entity_id FROM report_entities re "
        "JOIN reports r ON r.id = re.report_id WHERE r.status = 'approved'")
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    first_report = {}
    for row in links:
        find(row["report_id"])
        if row["entity_id"] in first_report:
            union(first_report[row["entity_id"]], row["report_id"])
        else:
            first_report[row["entity_id"]] = row["report_id"]
    approved = [r["id"] for r in db.execute("SELECT id FROM reports WHERE status = 'approved'")]
    groups = {}
    for report_id in approved:
        groups.setdefault(find(report_id), []).append(report_id)
    statements = [("DELETE FROM clusters", ())]
    for root, members in groups.items():
        for report_id in members:
            statements.append(("INSERT INTO clusters (report_id, cluster_id, size) VALUES (?, ?, ?)",
                               (report_id, root, len(members))))
    db.batch(statements)
    _index_cache.clear()


class NetworkIndex:
    """All approved entity links, loaded in two queries, for fast lookups."""

    def __init__(self, db):
        rows = db.execute(
            "SELECT e.kind, e.value, e.display, re.report_id, c.cluster_id, c.size "
            "FROM entities e JOIN report_entities re ON re.entity_id = e.id "
            "JOIN reports r ON r.id = re.report_id AND r.status = 'approved' "
            "LEFT JOIN clusters c ON c.report_id = r.id")
        self.by_key = {}
        self.cluster_names = {}
        for row in rows:
            entry = self.by_key.setdefault((row["kind"], row["value"]), {"reports": set(), "clusters": {}})
            entry["reports"].add(row["report_id"])
            if row["cluster_id"]:
                entry["clusters"][row["cluster_id"]] = row["size"]
                if row["kind"] in ("company", "app", "domain"):
                    names = self.cluster_names.setdefault(row["cluster_id"], [])
                    if row["display"] not in names:
                        names.append(row["display"])

    def lookup(self, kind, key):
        entry = self.by_key.get((kind, key))
        if not entry:
            return None
        cluster_id, size = max(entry["clusters"].items(), key=lambda kv: kv[1], default=(None, 0))
        return network.Hit(
            reports=len(entry["reports"]),
            cluster_reports=max(size, len(entry["reports"])),
            names=tuple(self.cluster_names.get(cluster_id, [])),
        )


_index_cache = {}
INDEX_TTL_SECONDS = 60


def network_index(db):
    cached = _index_cache.get(id(db))
    if cached and time.monotonic() - cached[0] < INDEX_TTL_SECONDS:
        return cached[1]
    index = NetworkIndex(db)
    _index_cache[id(db)] = (time.monotonic(), index)
    return index


def network_alerts(db, min_reports=2):
    """Groups of approved reports linked by shared entities."""
    rows = db.execute(
        "SELECT c.cluster_id, c.size, e.kind, e.display, r.scam_type FROM clusters c "
        "JOIN report_entities re ON re.report_id = c.report_id "
        "JOIN entities e ON e.id = re.entity_id "
        "JOIN reports r ON r.id = c.report_id "
        "WHERE c.size >= ? ORDER BY c.size DESC", (min_reports,))
    alerts = {}
    for row in rows:
        alert = alerts.setdefault(row["cluster_id"], {
            "id": row["cluster_id"], "reports": row["size"], "names": [], "links": {}, "types": []})
        if row["kind"] in ("company", "app", "domain") and row["display"] not in alert["names"]:
            alert["names"].append(row["display"])
        alert["links"][row["kind"]] = alert["links"].get(row["kind"], 0) + 1
        if row["scam_type"] not in alert["types"]:
            alert["types"].append(row["scam_type"])
    return sorted(alerts.values(), key=lambda a: -a["reports"])


# --- Public listing and search ----------------------------------------------------------

def _entities_for(db, report_ids):
    if not report_ids:
        return {}
    marks = ",".join("?" * len(report_ids))
    rows = db.execute(
        f"SELECT re.report_id, e.kind, e.value, e.display FROM report_entities re "
        f"JOIN entities e ON e.id = re.entity_id WHERE re.report_id IN ({marks})", tuple(report_ids))
    out = {}
    for row in rows:
        out.setdefault(row["report_id"], []).append(row)
    return out


def _public(row, entity_rows, cluster_size):
    shown = []
    for e in entity_rows:
        display = e["display"]
        if e["kind"] == "phone_hash":
            display = "A phone number (hidden)"
        elif e["kind"] == "account_hash":
            display = "A bank account (hidden)"
        shown.append({"kind": network._node_kind(e["kind"]), "display": display})
    return {
        "id": row["id"], "story": row["story"], "outcome": row["outcome"], "scam_type": row["scam_type"],
        "verdict": row["verdict"], "signals": json.loads(row["signals"]), "helped": row["helped"],
        "synthetic": bool(row["synthetic"]), "created_at": row["created_at"], "status": row["status"],
        "entities": shown, "network_size": cluster_size,
    }


def list_reports(db, query="", scam_type="", limit=50):
    rows = db.execute(
        "SELECT r.*, c.size AS cluster_size FROM reports r LEFT JOIN clusters c ON c.report_id = r.id "
        "WHERE r.status = 'approved' ORDER BY r.created_at DESC")
    if scam_type:
        rows = [r for r in rows if r["scam_type"] == scam_type]
    entities = _entities_for(db, [r["id"] for r in rows])
    query = (query or "").strip()
    if query:
        rows = [r for r in rows if _matches(query, r, entities.get(r["id"], []))]
    return [_public(r, entities.get(r["id"], []), r["cluster_size"]) for r in rows[:limit]]


def _matches(query, row, entity_rows):
    q = query.lower()
    candidates = {q, normalize.domain(query), normalize.company(query), normalize.wallet(query)}
    for e in entity_rows:
        if e["kind"] in ("phone_hash", "account_hash"):
            continue
        if e["value"] in candidates or q in e["display"].lower():
            return True
    return q in row["story"].lower()
