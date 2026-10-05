"""A flag: one finding, with the rule and source that produced it."""

from dataclasses import asdict, dataclass

RED = "red"
AMBER = "amber"


@dataclass(frozen=True)
class Flag:
    level: str            # RED or AMBER. There is no green.
    rule: str             # stable rule id, e.g. "returns.too_high"
    title: str            # one plain sentence for the user
    detail: str           # why, in plain words
    source: str           # where the rule or data comes from
    entity_kind: str = ""  # chain-map node this flag belongs to
    entity: str = ""       # display value of that node (never a phone or account number)
    snapshot_date: str = ""

    def to_dict(self):
        return asdict(self)


RULE_SOURCE = "ChainCheck rule"
