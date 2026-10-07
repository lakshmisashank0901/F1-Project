import base64
import json
import zlib

from app.feed import decode_compressed
from app.state import RaceState


def _drivers():
    return {
        "12": {
            "RacingNumber": "12",
            "Tla": "ANT",
            "LastName": "Antonelli",
            "TeamName": "Mercedes",
            "TeamColour": "00D2BE",
        },
        "1": {
            "RacingNumber": "1",
            "Tla": "VER",
            "LastName": "Verstappen",
            "TeamName": "Red Bull Racing",
            "TeamColour": "3671C6",
        },
    }


def test_snapshot_uses_track_name_and_sorts_race_order_separately_from_points():
    state = RaceState()
    state.set_season({"ANT": 280, "VER": 312}, {"Red Bull": 460, "Mercedes": 450})
    state.apply("DriverList", _drivers())
    state.apply(
        "TimingData",
        {
            "Lines": {
                "12": {"Position": "1", "GapToLeader": ""},
                "1": {"Position": "2", "GapToLeader": "+0.412"},
            }
        },
    )
    state.apply(
        "SessionInfo",
        {
            "Name": "Race",
            "Meeting": {
                "Location": "Suzuka",
                "Country": {"Name": "Japan"},
                "Circuit": {"ShortName": "Suzuka"},
            },
        },
    )

    snap = state.snapshot()
    assert snap["session"]["trackName"] == "Suzuka International Racing Course"
    assert snap["session"]["location"] == "Suzuka, Japan"
    assert [row["code"] for row in snap["raceOrder"]] == ["ANT", "VER"]
    assert snap["raceOrder"][1]["gap"] == "+0.412"
    assert [row["code"] for row in snap["drivers"]] == ["VER", "ANT"]
    assert snap["drivers"][0]["projected"] == 330
    assert snap["constructors"][0]["name"] == "Red Bull"


def test_timing_patch_moves_the_overtake_through_race_order_and_points():
    state = RaceState()
    state.set_season({"ANT": 280, "VER": 312, "RUS": 100, "TSU": 40}, {"Mercedes": 450, "Red Bull": 460})
    state.apply(
        "DriverList",
        {
            **_drivers(),
            "63": {"Tla": "RUS", "LastName": "Russell", "TeamName": "Mercedes", "TeamColour": "00D2BE"},
            "22": {"Tla": "TSU", "LastName": "Tsunoda", "TeamName": "RB", "TeamColour": "6692FF"},
        },
    )
    state.apply(
        "TimingData",
        {
            "Lines": {
                "12": {"Position": "1"},
                "1": {"Position": "2"},
                "63": {"Position": "5"},
                "22": {"Position": "8"},
            }
        },
    )
    state.apply("SessionInfo", {"Name": "Race", "Meeting": {"Circuit": {"ShortName": "Monza"}}})
    before = state.snapshot()

    state.apply("TimingData", {"Lines": {"1": {"Position": "1", "GapToLeader": ""}, "12": {"Position": "2", "GapToLeader": "+0.220"}}})
    after = state.snapshot()

    assert [row["name"] for row in before["constructors"][:2]] == ["Mercedes", "Red Bull"]
    assert [row["code"] for row in after["raceOrder"][:2]] == ["VER", "ANT"]
    assert [row["name"] for row in after["constructors"][:2]] == ["Red Bull", "Mercedes"]
    assert after["drivers"][0]["racePoints"] == 25


def test_position_stream_places_cars_and_draws_a_track_line():
    state = RaceState()
    state.set_season({}, {})
    state.apply("DriverList", _drivers())
    state.apply("SessionInfo", {"Name": "Race"})
    payload = {
        "Position": [
            {
                "Entries": {
                    "12": {"Status": "OnTrack", "X": 100, "Y": 400, "Z": 1},
                    "1": {"Status": "OnTrack", "X": 0, "Y": 0, "Z": 0},
                }
            }
        ]
    }
    encoded = base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
    state.apply("Position.z", decode_compressed(encoded))
    state.apply("Position.z", {"Position": [{"Entries": {"12": {"Status": "OnTrack", "X": 220, "Y": 380, "Z": 1}}}]})

    snap = state.snapshot()
    ant = next(car for car in snap["cars"] if car["code"] == "ANT")
    assert snap["track"][0] != snap["track"][-1]
    assert [ant["x"], ant["y"]] == snap["track"][-1]
    assert all(0 <= point[0] <= 100 and 0 <= point[1] <= 100 for point in snap["track"])


def test_retirement_flag_clears_race_points():
    state = RaceState()
    state.set_season({"ANT": 280}, {"Mercedes": 450})
    state.apply("DriverList", {"12": _drivers()["12"]})
    state.apply("TimingData", {"Lines": {"12": {"Position": "1", "Retired": True}}})
    state.apply("SessionInfo", {"Name": "Race"})
    snap = state.snapshot()
    assert snap["drivers"][0]["racePoints"] == 0
    assert snap["raceOrder"][0]["retired"] is True
