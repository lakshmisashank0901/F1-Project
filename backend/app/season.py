import httpx

DRIVER_URL = "https://api.jolpi.ca/ergast/f1/current/driverstandings.json?limit=100"
CONSTRUCTOR_URL = "https://api.jolpi.ca/ergast/f1/current/constructorstandings.json?limit=100"


def _lists(payload, key):
    try:
        return payload["MRData"]["StandingsTable"]["StandingsLists"][0][key]
    except (KeyError, IndexError, TypeError):
        return []


def parse_driver_points(payload):
    points = {}
    for row in _lists(payload, "DriverStandings"):
        code = ((row.get("Driver") or {}).get("code") or "").upper()
        if not code:
            continue
        points[code] = float(row.get("points") or 0)
    return points


def parse_constructor_points(payload):
    points = {}
    for row in _lists(payload, "ConstructorStandings"):
        name = (row.get("Constructor") or {}).get("name") or ""
        if not name:
            continue
        points[name] = float(row.get("points") or 0)
    return points


async def fetch_season():
    async with httpx.AsyncClient(timeout=20) as client:
        drivers = await client.get(DRIVER_URL)
        constructors = await client.get(CONSTRUCTOR_URL)
        drivers.raise_for_status()
        constructors.raise_for_status()
    return parse_driver_points(drivers.json()), parse_constructor_points(constructors.json())


def round_before(races, race_day):
    earlier = []
    for race in races:
        if not isinstance(race, dict):
            continue
        if (race.get("date") or "") < race_day:
            earlier.append(int(race["round"]))
    return max(earlier) if earlier else None


async def fetch_standings_before(year, race_start):
    race_day = race_start.date().isoformat()
    async with httpx.AsyncClient(timeout=20) as client:
        listing = await client.get(f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=100")
        if listing.status_code != 200:
            return await fetch_latest_standings(year)
        races = listing.json().get("MRData", {}).get("RaceTable", {}).get("Races") or []
        round_number = round_before(races, race_day)
        if round_number is None:
            return {}, {}
        drivers = await client.get(
            f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/driverstandings.json?limit=100"
        )
        constructors = await client.get(
            f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/constructorstandings.json?limit=100"
        )
        if drivers.status_code != 200 or constructors.status_code != 200:
            return await fetch_latest_standings(year)
    return parse_driver_points(drivers.json()), parse_constructor_points(constructors.json())


async def fetch_latest_standings(year):
    driver_url = f"https://api.jolpi.ca/ergast/f1/{year}/last/driverstandings.json?limit=100"
    constructor_url = f"https://api.jolpi.ca/ergast/f1/{year}/last/constructorstandings.json?limit=100"
    async with httpx.AsyncClient(timeout=20) as client:
        drivers = await client.get(driver_url)
        constructors = await client.get(constructor_url)
        if drivers.status_code != 200 or constructors.status_code != 200:
            return {}, {}
    return parse_driver_points(drivers.json()), parse_constructor_points(constructors.json())
