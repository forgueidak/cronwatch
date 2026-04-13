"""Tests for cronwatch.label."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from cronwatch.label import (
    LabelOptions,
    all_labels,
    filter_by_labels,
    group_by_label,
    matches_labels,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _Entry:
    name: str
    labels: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LabelOptions.from_dict
# ---------------------------------------------------------------------------

class TestLabelOptionsFromDict:
    def test_defaults(self):
        opts = LabelOptions.from_dict({})
        assert opts.include == []
        assert opts.exclude == []

    def test_full(self):
        opts = LabelOptions.from_dict({"include": ["a"], "exclude": ["b"]})
        assert opts.include == ["a"]
        assert opts.exclude == ["b"]


# ---------------------------------------------------------------------------
# matches_labels
# ---------------------------------------------------------------------------

def test_no_rules_matches_all():
    opts = LabelOptions()
    assert matches_labels(["x", "y"], opts) is True


def test_include_requires_overlap():
    opts = LabelOptions(include=["critical"])
    assert matches_labels(["critical", "nightly"], opts) is True
    assert matches_labels(["nightly"], opts) is False


def test_exclude_rejects_match():
    opts = LabelOptions(exclude=["skip"])
    assert matches_labels(["skip", "other"], opts) is False
    assert matches_labels(["other"], opts) is True


def test_include_and_exclude_combined():
    opts = LabelOptions(include=["critical"], exclude=["maintenance"])
    assert matches_labels(["critical"], opts) is True
    assert matches_labels(["critical", "maintenance"], opts) is False
    assert matches_labels(["maintenance"], opts) is False


def test_empty_labels_no_include_passes():
    opts = LabelOptions()
    assert matches_labels([], opts) is True


def test_empty_labels_with_include_fails():
    opts = LabelOptions(include=["critical"])
    assert matches_labels([], opts) is False


# ---------------------------------------------------------------------------
# filter_by_labels
# ---------------------------------------------------------------------------

def test_filter_keeps_matching_entries():
    entries = [
        _Entry("a", ["nightly"]),
        _Entry("b", ["weekly"]),
        _Entry("c", ["nightly", "critical"]),
    ]
    opts = LabelOptions(include=["nightly"])
    result = filter_by_labels(entries, opts)
    assert [e.name for e in result] == ["a", "c"]


def test_filter_works_with_dicts():
    entries = [
        {"name": "x", "labels": ["a"]},
        {"name": "y", "labels": ["b"]},
    ]
    opts = LabelOptions(include=["a"])
    result = filter_by_labels(entries, opts)
    assert len(result) == 1
    assert result[0]["name"] == "x"


# ---------------------------------------------------------------------------
# group_by_label
# ---------------------------------------------------------------------------

def test_group_by_label():
    entries = [
        _Entry("a", ["nightly", "critical"]),
        _Entry("b", ["nightly"]),
        _Entry("c", ["weekly"]),
    ]
    groups = group_by_label(entries)
    assert len(groups["nightly"]) == 2
    assert len(groups["critical"]) == 1
    assert len(groups["weekly"]) == 1


# ---------------------------------------------------------------------------
# all_labels
# ---------------------------------------------------------------------------

def test_all_labels_sorted_unique():
    entries = [
        _Entry("a", ["z", "a"]),
        _Entry("b", ["a", "m"]),
    ]
    assert all_labels(entries) == ["a", "m", "z"]


def test_all_labels_empty():
    assert all_labels([]) == []
