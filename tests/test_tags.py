"""Tests for cronwatch.tags module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from cronwatch.digest import DigestEntry
from cronwatch.tags import (
    TagFilter,
    all_tags,
    filter_by_tags,
    group_by_tag,
)


def _make_entry(command: str, tags: Optional[List[str]] = None) -> DigestEntry:
    return DigestEntry(
        command=command,
        total=1,
        failures=0,
        last_run="2024-01-01T00:00:00",
        last_status="success",
        tags=tags or [],
    )


class TestTagFilter:
    def test_no_rules_matches_all(self):
        f = TagFilter()
        assert f.matches(_make_entry("cmd", ["foo"]))
        assert f.matches(_make_entry("cmd", []))

    def test_include_rule_requires_overlap(self):
        f = TagFilter(include=["billing"])
        assert f.matches(_make_entry("cmd", ["billing", "nightly"]))
        assert not f.matches(_make_entry("cmd", ["debug"]))

    def test_exclude_rule_rejects_match(self):
        f = TagFilter(exclude=["dry-run"])
        assert not f.matches(_make_entry("cmd", ["dry-run"]))
        assert f.matches(_make_entry("cmd", ["billing"]))

    def test_include_and_exclude_combined(self):
        f = TagFilter(include=["nightly"], exclude=["debug"])
        assert f.matches(_make_entry("cmd", ["nightly"]))
        assert not f.matches(_make_entry("cmd", ["nightly", "debug"]))
        assert not f.matches(_make_entry("cmd", ["billing"]))

    def test_untagged_entry_excluded_when_include_set(self):
        f = TagFilter(include=["billing"])
        assert not f.matches(_make_entry("cmd", []))


def test_filter_by_tags_returns_subset():
    entries = [
        _make_entry("a", ["billing"]),
        _make_entry("b", ["debug"]),
        _make_entry("c", ["nightly"]),
    ]
    result = filter_by_tags(entries, TagFilter(include=["billing", "nightly"]))
    commands = [e.command for e in result]
    assert "a" in commands
    assert "c" in commands
    assert "b" not in commands


def test_group_by_tag_multi_tag_entry_appears_in_both():
    entry = _make_entry("cmd", ["billing", "nightly"])
    groups = group_by_tag([entry])
    assert "billing" in groups
    assert "nightly" in groups
    assert groups["billing"][0].command == "cmd"


def test_group_by_tag_untagged_key():
    entry = _make_entry("cmd", [])
    groups = group_by_tag([entry])
    assert "__untagged__" in groups


def test_all_tags_sorted_unique():
    entries = [
        _make_entry("a", ["zebra", "apple"]),
        _make_entry("b", ["apple", "mango"]),
    ]
    tags = all_tags(entries)
    assert tags == ["apple", "mango", "zebra"]


def test_all_tags_empty_entries():
    assert all_tags([]) == []
