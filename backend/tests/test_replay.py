from datetime import datetime, timezone

from app.replay_data import format_gap, latest_at, latest_finished_race
from app.season import round_before


def test_round_before_uses_the_previous_race():
    races = [
        {"round": "14", "date": "2026-09-13"},
        {"round": "15", "date": "2026-09-26"},
        {"round": "16", "date": "2026-10-04"},
    ]
    assert round_before(races, "2026-09-26") == 14


def test_latest_finished_race_skips_races_that_have_not_started():
    sessions = [
        {"session_name": "Race", "date_start": "2026-09-01T07:00:00+00:00", "session_key": 1},
        {"session_name": "Race", "date_start": "2026-10-04T07:00:00+00:00", "session_key": 2},
        {"session_name": "Race", "date_start": "2026-11-22T04:00:00+00:00", "session_key": 3},
        {"session_name": "Qualifying", "date_start": "2026-10-03T07:00:00+00:00", "session_key": 4},
    ]
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    chosen = latest_finished_race(sessions, now)
    assert chosen["session_key"] == 2


def test_outline_uses_the_car_that_covers_the_most_of_the_lap():
    from app.replay import build_outline, _spread

    rows = [
        {"driver_number": 1, "date": "2026-10-04T07:00:00+00:00", "x": 0, "y": 0},
        {"driver_number": 1, "date": "2026-10-04T07:00:01+00:00", "x": 10, "y": 10},
        {"driver_number": 1, "date": "2026-10-04T07:00:02+00:00", "x": 80, "y": 10},
        {"driver_number": 2, "date": "2026-10-04T07:00:00+00:00", "x": 5, "y": 5},
    ]
    assert build_outline(rows) == [(10, 10), (80, 10)]
    assert _spread([{"x": 1888, "y": -929}, {"x": 1888, "y": -929}]) == 0
    assert _spread([{"x": 10, "y": 10}, {"x": 410, "y": 10}]) == 400
    records = [
        {"date": "2026-10-04T07:00:00+00:00", "position": 2},
        {"date": "2026-10-04T07:10:00+00:00", "position": 1},
    ]
    moment = datetime(2026, 10, 4, 7, 5, tzinfo=timezone.utc)
    assert latest_at(records, moment)["position"] == 2
    assert format_gap(1, 0) == "LEAD"
    assert format_gap(2, 1.25) == "+1.250"
