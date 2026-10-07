import pytest

from app.standings import project_standings, race_points


def test_race_points_follow_the_top_ten_scale():
    assert [race_points(pos, "Race") for pos in range(1, 12)] == [
        25, 18, 15, 12, 10, 8, 6, 4, 2, 1, 0
    ]


def test_sprint_points_use_the_shorter_scale():
    assert [race_points(pos, "Sprint") for pos in range(1, 10)] == [
        8, 7, 6, 5, 4, 3, 2, 1, 0
    ]


def test_a_retirement_scores_nothing_even_if_a_position_is_still_present():
    assert race_points(1, "Race", retired=True) == 0


def test_driver_table_sorts_by_projected_points_not_track_position():
    rows = project_standings(
        cars=[
            {"code": "ANT", "team": "Mercedes", "color": "00D2BE", "position": 1, "retired": False},
            {"code": "VER", "team": "Red Bull", "color": "3671C6", "position": 2, "retired": False},
        ],
        driver_season={"ANT": 280, "VER": 312},
        constructor_season={"Mercedes": 450, "Red Bull": 460},
        session="Race",
    )

    assert [row["code"] for row in rows["drivers"]] == ["VER", "ANT"]
    assert rows["drivers"][0]["projected"] == 330
    assert rows["drivers"][0]["race_points"] == 18
    assert rows["drivers"][1]["projected"] == 305
    assert rows["drivers"][1]["race_points"] == 25


def test_overtake_moves_race_points_and_can_reorder_constructors():
    before = project_standings(
        cars=[
            {"code": "ANT", "team": "Mercedes", "color": "00D2BE", "position": 1, "retired": False},
            {"code": "RUS", "team": "Mercedes", "color": "00D2BE", "position": 5, "retired": False},
            {"code": "VER", "team": "Red Bull", "color": "3671C6", "position": 2, "retired": False},
            {"code": "TSU", "team": "Red Bull", "color": "3671C6", "position": 8, "retired": False},
        ],
        driver_season={"ANT": 280, "RUS": 100, "VER": 312, "TSU": 40},
        constructor_season={"Mercedes": 450, "Red Bull": 460},
        session="Race",
    )
    after = project_standings(
        cars=[
            {"code": "VER", "team": "Red Bull", "color": "3671C6", "position": 1, "retired": False},
            {"code": "ANT", "team": "Mercedes", "color": "00D2BE", "position": 2, "retired": False},
            {"code": "RUS", "team": "Mercedes", "color": "00D2BE", "position": 5, "retired": False},
            {"code": "TSU", "team": "Red Bull", "color": "3671C6", "position": 8, "retired": False},
        ],
        driver_season={"ANT": 280, "RUS": 100, "VER": 312, "TSU": 40},
        constructor_season={"Mercedes": 450, "Red Bull": 460},
        session="Race",
    )

    assert [row["name"] for row in before["constructors"]] == ["Mercedes", "Red Bull"]
    assert before["constructors"][0]["projected"] == 485
    assert before["constructors"][0]["race_points"] == 35
    assert before["constructors"][1]["projected"] == 482

    assert [row["name"] for row in after["constructors"]] == ["Red Bull", "Mercedes"]
    assert after["constructors"][0]["projected"] == 489
    assert after["drivers"][0]["code"] == "VER"
    assert after["drivers"][0]["race_points"] == 25


def test_retirement_drops_that_car_and_the_constructor_total():
    rows = project_standings(
        cars=[
            {"code": "ANT", "team": "Mercedes", "color": "00D2BE", "position": 1, "retired": True},
            {"code": "RUS", "team": "Mercedes", "color": "00D2BE", "position": 5, "retired": False},
        ],
        driver_season={"ANT": 280, "RUS": 100},
        constructor_season={"Mercedes": 450},
        session="Race",
    )

    ant = next(row for row in rows["drivers"] if row["code"] == "ANT")
    assert ant["race_points"] == 0
    assert ant["projected"] == 280
    assert rows["constructors"][0]["race_points"] == 10
    assert rows["constructors"][0]["projected"] == 460
