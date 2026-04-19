"""Tests for cronwatch.notifier_filter_watcher."""
from cronwatch.notifier_filter import NotifierFilterOptions
from cronwatch.notifier_filter_watcher import (
    NotifierFilterWatchOptions,
    should_send_notification,
    format_suppression_notice,
)
from cronwatch.runner import JobResult


def _make_result(exit_code=0, stderr="", duration=1.0) -> JobResult:
    return JobResult(
        command="backup.sh",
        exit_code=exit_code,
        stdout="",
        stderr=stderr,
        duration=duration,
        timed_out=False,
    )


class TestNotifierFilterWatchOptionsFromDict:
    def test_defaults_when_key_missing(self):
        o = NotifierFilterWatchOptions.from_dict({})
        assert o.filter.enabled is True

    def test_reads_nested_key(self):
        o = NotifierFilterWatchOptions.from_dict({
            "notifier_filter": {"only_on_failure": True}
        })
        assert o.filter.only_on_failure is True

    def test_post_init_sets_default_filter(self):
        o = NotifierFilterWatchOptions()
        assert isinstance(o.filter, NotifierFilterOptions)


def test_should_send_no_opts_returns_true():
    d = should_send_notification(_make_result(), None)
    assert d.should_notify is True


def test_should_send_passes_through_filter():
    opts = NotifierFilterWatchOptions(
        filter=NotifierFilterOptions(only_on_failure=True)
    )
    d = should_send_notification(_make_result(exit_code=0), opts)
    assert d.should_notify is False


def test_should_send_failure_allowed():
    opts = NotifierFilterWatchOptions(
        filter=NotifierFilterOptions(only_on_failure=True)
    )
    d = should_send_notification(_make_result(exit_code=1), opts)
    assert d.should_notify is True


def test_format_suppression_notice_contains_command():
    from cronwatch.notifier_filter import FilterDecision
    d = FilterDecision(should_notify=False, reason="only_on_failure: job succeeded")
    msg = format_suppression_notice(d, "backup.sh")
    assert "backup.sh" in msg
    assert "only_on_failure" in msg
    assert "suppressed" in msg
