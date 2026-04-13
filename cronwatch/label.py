"""Label-based job grouping and filtering for cronwatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class LabelOptions:
    """Options for label-based filtering."""
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "LabelOptions":
        return cls(
            include=list(data.get("include", [])),
            exclude=list(data.get("exclude", [])),
        )


def matches_labels(job_labels: Iterable[str], opts: LabelOptions) -> bool:
    """Return True if *job_labels* satisfies the include/exclude rules.

    - If *include* is non-empty, the job must have at least one matching label.
    - If *exclude* is non-empty, the job must have no matching labels.
    """
    job_set = set(job_labels)

    if opts.exclude and job_set & set(opts.exclude):
        return False

    if opts.include and not (job_set & set(opts.include)):
        return False

    return True


def filter_by_labels(
    entries: Iterable,
    opts: LabelOptions,
    *,
    label_attr: str = "labels",
) -> List:
    """Filter *entries* by their labels using *opts*.

    Each entry is expected to have an attribute (or key) named *label_attr*
    that is an iterable of strings.  Entries without that attribute are
    treated as having no labels.
    """
    result = []
    for entry in entries:
        if isinstance(entry, dict):
            labels = entry.get(label_attr, [])
        else:
            labels = getattr(entry, label_attr, [])
        if matches_labels(labels, opts):
            result.append(entry)
    return result


def group_by_label(entries: Iterable, *, label_attr: str = "labels") -> Dict[str, List]:
    """Return a mapping of label -> list of entries that carry that label."""
    groups: Dict[str, List] = {}
    for entry in entries:
        if isinstance(entry, dict):
            labels = entry.get(label_attr, [])
        else:
            labels = getattr(entry, label_attr, [])
        for lbl in labels:
            groups.setdefault(lbl, []).append(entry)
    return groups


def all_labels(entries: Iterable, *, label_attr: str = "labels") -> List[str]:
    """Return a sorted, deduplicated list of every label seen across *entries*."""
    seen = set()
    for entry in entries:
        if isinstance(entry, dict):
            labels = entry.get(label_attr, [])
        else:
            labels = getattr(entry, label_attr, [])
        seen.update(labels)
    return sorted(seen)
