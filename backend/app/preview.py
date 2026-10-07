import asyncio

from app.state import RaceState


ANCHORS = [
    (140, 300),
    (150, 170),
    (240, 90),
    (380, 70),
    (520, 120),
    (600, 210),
    (610, 300),
    (520, 360),
    (360, 350),
    (230, 390),
    (160, 450),
    (300, 470),
    (480, 450),
    (620, 380),
    (660, 280),
    (580, 170),
    (430, 150),
    (300, 200),
    (210, 270),
    (170, 340),
]


def _catmull(points, samples=16):
    if len(points) < 4:
        return list(points)
    ring = [points[-1], *points, points[0], points[1]]
    outline = []
    for index in range(1, len(ring) - 2):
        p0, p1, p2, p3 = ring[index - 1 : index + 3]
        for step in range(samples):
            t = step / samples
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            outline.append((x, y))
    return outline


def _along(outline, distance):
    if not outline:
        return (0, 0)
    scaled = (distance % 1) * (len(outline) - 1)
    index = min(int(scaled), len(outline) - 2)
    frac = scaled - index
    start, end = outline[index], outline[index + 1]
    return (
        start[0] + (end[0] - start[0]) * frac,
        start[1] + (end[1] - start[1]) * frac,
    )


DRIVERS = [
    {"number": "12", "code": "ANT", "name": "Antonelli", "team": "Mercedes", "color": "00D2BE", "season": 280, "distance": 50.00, "speed": 0.0050},
    {"number": "1", "code": "VER", "name": "Verstappen", "team": "Red Bull", "color": "3671C6", "season": 312, "distance": 49.70, "speed": 0.0090},
    {"number": "4", "code": "NOR", "name": "Norris", "team": "McLaren", "color": "FF8000", "season": 260, "distance": 49.40, "speed": 0.0049},
    {"number": "16", "code": "LEC", "name": "Leclerc", "team": "Ferrari", "color": "E8002D", "season": 240, "distance": 49.00, "speed": 0.0048},
    {"number": "63", "code": "RUS", "name": "Russell", "team": "Mercedes", "color": "00D2BE", "season": 100, "distance": 48.60, "speed": 0.0047},
    {"number": "81", "code": "PIA", "name": "Piastri", "team": "McLaren", "color": "FF8000", "season": 90, "distance": 48.20, "speed": 0.0046},
    {"number": "44", "code": "HAM", "name": "Hamilton", "team": "Ferrari", "color": "E8002D", "season": 80, "distance": 47.80, "speed": 0.0045},
    {"number": "22", "code": "TSU", "name": "Tsunoda", "team": "Red Bull", "color": "3671C6", "season": 40, "distance": 47.20, "speed": 0.0044},
]


async def run_preview(state: RaceState, publish):
    outline = _catmull(ANCHORS)
    state.track_raw = outline
    state.set_season(
        {row["code"]: row["season"] for row in DRIVERS},
        {"Mercedes": 450, "Red Bull": 460, "McLaren": 420, "Ferrari": 400},
    )
    state.apply(
        "DriverList",
        {
            row["number"]: {
                "RacingNumber": row["number"],
                "Tla": row["code"],
                "LastName": row["name"],
                "TeamName": row["team"],
                "TeamColour": row["color"],
            }
            for row in DRIVERS
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
    field = [dict(row) for row in DRIVERS]
    while True:
        for row in field:
            row["distance"] += row["speed"]
        ranking = sorted(field, key=lambda row: row["distance"], reverse=True)
        leader = ranking[0]["distance"]
        lines = {}
        for index, row in enumerate(ranking, start=1):
            state.positions[row["number"]] = _along(outline, row["distance"])
            gap = "LEAD" if index == 1 else f"+{(leader - row['distance']) * 8:.3f}"
            lines[row["number"]] = {"Position": str(index), "GapToLeader": gap, "Retired": False}
        state.lines = lines
        snap = state.snapshot()
        snap["status"] = "preview"
        snap["preview"] = True
        await publish(snap)
        await asyncio.sleep(0.1)
