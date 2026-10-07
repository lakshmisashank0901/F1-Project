RACE_SCALE = (25, 18, 15, 12, 10, 8, 6, 4, 2, 1)
SPRINT_SCALE = (8, 7, 6, 5, 4, 3, 2, 1)


def race_points(position: int, session: str, retired: bool = False) -> int:
    if retired:
        return 0
    kind = (session or "").strip().lower()
    if kind == "sprint":
        scale = SPRINT_SCALE
    elif kind == "race":
        scale = RACE_SCALE
    else:
        return 0
    if position is None or position < 1 or position > len(scale):
        return 0
    return scale[position - 1]


def project_standings(cars, driver_season, constructor_season, session):
    drivers = []
    for car in cars:
        points = race_points(car.get("position"), session, bool(car.get("retired")))
        season = driver_season.get(car["code"], 0)
        drivers.append(
            {
                "code": car["code"],
                "name": car.get("name") or car["code"],
                "team": car.get("team") or "",
                "color": car.get("color") or "888888",
                "position": car.get("position") or 99,
                "retired": bool(car.get("retired")),
                "season": season,
                "race_points": points,
                "projected": season + points,
            }
        )
    drivers.sort(key=lambda row: (-row["projected"], row["position"], row["code"]))

    teams = {}
    for row in drivers:
        team = teams.setdefault(
            row["team"],
            {
                "name": row["team"],
                "color": row["color"],
                "season": constructor_season.get(row["team"], 0),
                "race_points": 0,
                "drivers": [],
            },
        )
        team["race_points"] += row["race_points"]
        team["drivers"].append({"code": row["code"], "race_points": row["race_points"]})
    constructors = []
    for team in teams.values():
        team["projected"] = team["season"] + team["race_points"]
        team["drivers"].sort(key=lambda item: (-item["race_points"], item["code"]))
        constructors.append(team)
    constructors.sort(key=lambda row: (-row["projected"], row["name"]))
    return {"drivers": drivers, "constructors": constructors}
