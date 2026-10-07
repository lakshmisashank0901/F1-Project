import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.replay_data import format_gap, latest_at, parse_time
from app.season import fetch_standings_before

API = "https://api.openf1.org/v1"
RACE_SECONDS_PER_TICK = 12
TICK_SECONDS = 0.25
OUTLINE_CACHE = Path(__file__).resolve().parents[1] / "data" / "outline.json"
logger = logging.getLogger("replay")


def _rows(payload):
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _spread(rows):
    xs = []
    ys = []
    for row in _rows(rows):
        x = float(row.get("x") or 0)
        y = float(row.get("y") or 0)
        if x == 0 and y == 0:
            continue
        xs.append(x)
        ys.append(y)
    if len(xs) < 2:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _cached_outline(session_key):
    try:
        data = json.loads(OUTLINE_CACHE.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if data.get("session_key") != session_key:
        return []
    return [(float(point[0]), float(point[1])) for point in data.get("points") or []]


def _store_outline(session_key, points):
    OUTLINE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    OUTLINE_CACHE.write_text(json.dumps({"session_key": session_key, "points": points}))


def _group(rows):
    grouped = {}
    for row in _rows(rows):
        grouped.setdefault(str(row["driver_number"]), []).append(row)
    for items in grouped.values():
        items.sort(key=lambda row: row["date"])
    return grouped


def _driver_payload(drivers):
    payload = {}
    for driver in drivers:
        number = str(driver["driver_number"])
        payload[number] = {
            "RacingNumber": number,
            "Tla": driver.get("name_acronym") or number,
            "LastName": driver.get("last_name") or driver.get("full_name") or number,
            "TeamName": driver.get("team_name") or "",
            "TeamColour": driver.get("team_colour") or "888888",
        }
    return payload


def _stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def build_outline(rows):
    grouped = {}
    for row in rows:
        x = float(row.get("x") or 0)
        y = float(row.get("y") or 0)
        if x == 0 and y == 0:
            continue
        grouped.setdefault(str(row["driver_number"]), []).append((row["date"], (x, y)))
    best = []
    for points in grouped.values():
        points.sort(key=lambda item: item[0])
        path = []
        for _, point in points:
            if not path or _moved(path[-1], point):
                path.append(point)
        if len(path) > len(best):
            best = path
    return best


def _moved(previous, point):
    dx = previous[0] - point[0]
    dy = previous[1] - point[1]
    return dx * dx + dy * dy > 900


async def _get(client, url, params=None):
    delay = 3
    for _ in range(8):
        response = await client.get(url, params=params)
        if response.status_code == 429:
            logger.warning("openf1 rate limit, waiting %ss", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 40)
            continue
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return _rows(response.json())
    raise RuntimeError("OpenF1 rate limit did not clear")


async def _locations(client, session_key, start, end, driver_number=None):
    query = f"/v1/location?session_key={session_key}&date>={_stamp(start)}&date<={_stamp(end)}"
    if driver_number is not None:
        query += f"&driver_number={driver_number}"
    return await _get(
        client,
        httpx.URL(scheme="https", host="api.openf1.org", raw_path=query.encode()),
    )


async def _moving_outline(client, session, driver_number):
    key = session["session_key"]
    cached = _cached_outline(key)
    if len(cached) >= 2:
        return cached
    start = parse_time(session["date_start"]) + timedelta(minutes=12)
    probe = await _locations(client, key, start, start + timedelta(seconds=20), driver_number)
    if _spread(probe) < 200:
        return []
    path = build_outline(
        await _locations(client, key, start, start + timedelta(seconds=100), driver_number)
    )
    if len(path) >= 2:
        _store_outline(key, path)
    return path


async def run_free_replay(state, publish):
    async with httpx.AsyncClient(timeout=40) as client:
        while True:
            try:
                await _play(client, state, publish)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("free replay failed")
                snapshot = state.snapshot()
                snapshot["status"] = "offline"
                snapshot["preview"] = False
                await publish(snapshot)
                await asyncio.sleep(5)


async def _play(client, state, publish):
    sessions = await _get(
        client,
        f"{API}/sessions",
        {"session_name": "Race", "year": datetime.now(timezone.utc).year},
    )
    now = datetime.now(timezone.utc)
    finished = [
        session
        for session in sessions
        if (session.get("session_name") or session.get("session_type")) == "Race"
        and parse_time(session["date_start"]) <= now
    ]
    finished.sort(key=lambda session: session["date_start"], reverse=True)
    session = None
    drivers = []
    outline = []
    for candidate in finished:
        drivers = await _get(client, f"{API}/drivers", {"session_key": candidate["session_key"]})
        if not drivers:
            continue
        outline = await _moving_outline(client, candidate, drivers[0]["driver_number"])
        if len(outline) >= 2:
            session = candidate
            break
    if session is None:
        raise RuntimeError("No race with a circuit map is available")

    key = session["session_key"]
    positions = await _get(client, f"{API}/position", {"session_key": key})
    intervals = await _get(client, f"{API}/intervals", {"session_key": key})
    if not positions:
        raise RuntimeError("Race data is not available yet")
    try:
        driver_points, team_points = await fetch_standings_before(
            session["year"], parse_time(session["date_start"])
        )
    except Exception:
        driver_points, team_points = {}, {}

    state.positions = {}
    state.lines = {}
    state.set_season(driver_points, team_points)
    state.apply("DriverList", _driver_payload(drivers))
    state.apply(
        "SessionInfo",
        {
            "Name": "Race",
            "Meeting": {
                "Location": session.get("location") or "",
                "Country": {"Name": session.get("country_name") or ""},
                "Circuit": {"ShortName": session.get("circuit_short_name") or session.get("location") or ""},
            },
        },
    )

    by_position = _group(positions)
    by_gap = _group(intervals)
    start = min(parse_time(row["date"]) for row in positions)
    end = max(parse_time(row["date"]) for row in positions)
    scheduled = parse_time(session["date_start"])
    playhead = scheduled if start < scheduled < end else start
    loaded_until = playhead
    samples = {}
    state.track_raw = outline

    while playhead <= end:
        target = min(playhead + timedelta(seconds=45), end)
        while loaded_until < target:
            chunk_end = min(loaded_until + timedelta(seconds=15), end)
            if chunk_end <= loaded_until:
                break
            for row in await _locations(client, key, loaded_until, chunk_end):
                samples.setdefault(str(row["driver_number"]), []).append(row)
            loaded_until = chunk_end
            for rows in samples.values():
                rows.sort(key=lambda row: row["date"])
        _frame(state, by_position, by_gap, samples, playhead)
        snapshot = state.snapshot()
        snapshot["status"] = "replay"
        snapshot["preview"] = False
        await publish(snapshot)
        await asyncio.sleep(TICK_SECONDS)
        playhead += timedelta(seconds=RACE_SECONDS_PER_TICK)


def _frame(state, by_position, by_gap, samples, playhead):
    lines = {}
    for number, records in by_position.items():
        record = latest_at(records, playhead)
        if not record:
            continue
        position = int(record["position"])
        gap_row = latest_at(by_gap.get(number, []), playhead)
        gap = None if gap_row is None else gap_row.get("gap_to_leader")
        lines[number] = {
            "Position": str(position),
            "GapToLeader": format_gap(position, gap),
            "Retired": False,
        }
        sample = latest_at(samples.get(number, []), playhead)
        if not sample:
            continue
        point = (float(sample["x"]), float(sample["y"]))
        if point == (0.0, 0.0):
            continue
        state.positions[number] = point
    state.lines = lines
