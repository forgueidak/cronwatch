import pytest
from datetime import datetime
from cronwatch.suppress import SuppressOptions, check_suppress, SuppressResult


def _opts(**kwargs) -> SuppressOptions:
    base = {"enabled": True}
    base.update(kwargs)
    return SuppressOptions.from_dict(base)


def test_disabled_never_suppresses():
    opts = SuppressOptions.from_dict({"enabled": False, "exit_codes": [0]})
    result = check_suppress(opts, exit_code=0)
    assert not result.suppressed


def test_exit_code_match_suppresses():
    opts = _opts(exit_codes=[0, 75])
    result = check_suppress(opts, exit_code=75)
    assert result.suppressed
    assert "75" in result.reason


def test_exit_code_no_match_passes():
    opts = _opts(exit_codes=[0])
    result = check_suppress(opts, exit_code=1)
    assert not result.suppressed


def test_time_window_inside_suppresses():
    opts = _opts(time_windows=[{"start": "02:00", "end": "04:00"}])
    dt = datetime(2024, 1, 15, 3, 0)  # 03:00
    result = check_suppress(opts, exit_code=1, now=dt)
    assert result.suppressed
    assert "02:00" in result.reason


def test_time_window_outside_passes():
    opts = _opts(time_windows=[{"start": "02:00", "end": "04:00"}])
    dt = datetime(2024, 1, 15, 10, 0)
    result = check_suppress(opts, exit_code=1, now=dt)
    assert not result.suppressed


def test_overnight_window_suppresses():
    opts = _opts(time_windows=[{"start": "23:00", "end": "01:00"}])
    dt = datetime(2024, 1, 15, 23, 30)
    result = check_suppress(opts, exit_code=1, now=dt)
    assert result.suppressed


def test_overnight_window_early_morning_suppresses():
    opts = _opts(time_windows=[{"start": "23:00", "end": "01:00"}])
    dt = datetime(2024, 1, 15, 0, 45)
    result = check_suppress(opts, exit_code=1, now=dt)
    assert result.suppressed


def test_weekday_suppresses():
    opts = _opts(weekdays=[5, 6])
    dt = datetime(2024, 1, 13)  # Saturday = weekday 5
    result = check_suppress(opts, exit_code=1, now=dt)
    assert result.suppressed
    assert "5" in result.reason


def test_weekday_not_in_list_passes():
    opts = _opts(weekdays=[5, 6])
    dt = datetime(2024, 1, 15)  # Monday = 0
    result = check_suppress(opts, exit_code=1, now=dt)
    assert not result.suppressed


def test_suppress_result_ok_and_summary():
    r = SuppressResult(suppressed=True, reason="exit code 0")
    assert not r.ok()
    assert "suppressed" in r.summary()

    r2 = SuppressResult(suppressed=False)
    assert r2.ok()
    assert "not suppressed" in r2.summary()


def test_from_dict_defaults():
    opts = SuppressOptions.from_dict({})
    assert not opts.enabled
    assert opts.exit_codes == []
    assert opts.time_windows == []
    assert opts.weekdays == []
