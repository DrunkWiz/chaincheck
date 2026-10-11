"""Every check is code (docs/BUILD_BRIEF.md §7). Each takes the merged entities
and a Context and returns a list of Flags."""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from backend.snapshots import Snapshot


@dataclass
class Context:
    fid: Snapshot
    ial: Snapshot
    today: date
    # domain -> creation date, or None when the lookup failed
    rdap: Callable[[str], Optional[date]]
    # (kind, key) -> network.Hit or None. None when no community data.
    network: Optional[Callable] = None
    secret: Optional[str] = None
    # Filled in by the MAS check for later checks.
    on_record_domains: set = field(default_factory=set)
    on_record_phones: set = field(default_factory=set)
    copycat_of: set = field(default_factory=set)   # licensed firm keys flagged as copied
    matched_firms: set = field(default_factory=set)  # licensed firms whose given contacts all match MAS
    company_flagged: bool = False                     # any company check raised a flag
    # Things to check yourself that aren't flags (they don't change the verdict).
    verify_yourself: list = field(default_factory=list)
