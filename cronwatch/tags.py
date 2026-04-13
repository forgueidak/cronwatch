"""Tag-based filtering and grouping for cron job history entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from cronwatch.digest import DigestEntry


@dataclass
class TagFilter:
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

    def matches(self, entry: DigestEntry) -> bool:
        """Return True if entry tags satisfy include/exclude rules."""
        entry_tags = set(entry.tags if entry.tags else [])

        if self.include and not entry_tags.intersection(self.include):
            return False
        if self.exclude and entry_tags.intersection(self.exclude):
            return False
        return True


def filter_by_tags(entries: List[DigestEntry], tag_filter: TagFilter) -> List[DigestEntry]:
    """Return only entries that match the given TagFilter."""
    return [e for e in entries if tag_filter.matches(e)]


def group_by_tag(entries: List[DigestEntry]) -> Dict[str, List[DigestEntry]]:
    """Group entries by each of their tags. An entry may appear under multiple tags.

    Entries with no tags appear under the key '__untagged__'.
    """
    groups: Dict[str, List[DigestEntry]] = {}
    for entry in entries:
        tags = entry.tags if entry.tags else []
        if not tags:
            groups.setdefault("__untagged__", []).append(entry)
        else:
            for tag in tags:
                groups.setdefault(tag, []).append(entry)
    return groups


def all_tags(entries: List[DigestEntry]) -> List[str]:
    """Return a sorted list of unique tags found across all entries."""
    seen = set()
    for entry in entries:
        for tag in (entry.tags or []):
            seen.add(tag)
    return sorted(seen)
