from app.standings import project_standings

CIRCUIT_NAMES = {
    "albert park": "Albert Park Circuit",
    "bahrain": "Bahrain International Circuit",
    "sakhir": "Bahrain International Circuit",
    "jeddah": "Jeddah Corniche Circuit",
    "melbourne": "Albert Park Circuit",
    "suzuka": "Suzuka International Racing Course",
    "shanghai": "Shanghai International Circuit",
    "miami": "Miami International Autodrome",
    "imola": "Autodromo Enzo e Dino Ferrari",
    "monaco": "Circuit de Monaco",
    "monte carlo": "Circuit de Monaco",
    "barcelona": "Circuit de Barcelona-Catalunya",
    "catalunya": "Circuit de Barcelona-Catalunya",
    "montreal": "Circuit Gilles Villeneuve",
    "silverstone": "Silverstone Circuit",
    "spielberg": "Red Bull Ring",
    "spa": "Circuit de Spa-Francorchamps",
    "spa-francorchamps": "Circuit de Spa-Francorchamps",
    "hungaroring": "Hungaroring",
    "budapest": "Hungaroring",
    "zandvoort": "Circuit Zandvoort",
    "monza": "Autodromo Nazionale Monza",
    "baku": "Baku City Circuit",
    "singapore": "Marina Bay Street Circuit",
    "marina bay": "Marina Bay Street Circuit",
    "austin": "Circuit of the Americas",
    "mexico city": "Autodromo Hermanos Rodriguez",
    "interlagos": "Autodromo Jose Carlos Pace",
    "sao paulo": "Autodromo Jose Carlos Pace",
    "las vegas": "Las Vegas Strip Circuit",
    "lusail": "Lusail International Circuit",
    "losail": "Lusail International Circuit",
    "yas marina": "Yas Marina Circuit",
    "yas island": "Yas Marina Circuit",
}


def _merge(base, delta):
    if isinstance(base, dict) and isinstance(delta, dict):
        merged = dict(base)
        for key, value in delta.items():
            merged[key] = _merge(merged[key], value) if key in merged else value
        return merged
    return delta


def _match_team(feed_name, known_names):
    feed = (feed_name or "").strip()
    feed_l = feed.lower()
    best = None
    for name in known_names:
        key = name.lower()
        if feed_l == key or key in feed_l or (feed_l and feed_l in key):
            if best is None or len(name) > len(best):
                best = name
    return best or feed


def _session_kind(info):
    name = str((info or {}).get("Name") or (info or {}).get("Type") or "")
    lower = name.lower()
    if "sprint" in lower and "qualifying" not in lower and "shootout" not in lower:
        return "Sprint"
    if "race" in lower:
        return "Race"
    return "Other"


def _country_name(meeting):
    country = meeting.get("Country")
    if isinstance(country, dict):
        return country.get("Name") or ""
    return country or ""


def _track_title(info):
    meeting = (info or {}).get("Meeting") or {}
    circuit = meeting.get("Circuit") or {}
    short = circuit.get("ShortName") or meeting.get("Name") or ""
    track_name = CIRCUIT_NAMES.get(short.strip().lower(), short or "Live session")
    city = meeting.get("Location") or ""
    country = _country_name(meeting)
    if city and country and country.lower() not in city.lower():
        location = f"{city}, {country}"
    else:
        location = city or country
    return track_name, location


def _coords(entry):
    if not isinstance(entry, dict):
        return None
    x = entry.get("X", entry.get("x"))
    y = entry.get("Y", entry.get("y"))
    if x is None or y is None:
        return None
    if float(x) == 0 and float(y) == 0:
        return None
    return float(x), float(y)


def _normalize(points):
    if not points:
        return []
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)
    pad_x = span_x * 0.08
    pad_y = span_y * 0.08
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    span_x = max_x - min_x
    span_y = max_y - min_y

    def place(point):
        x = (point[0] - min_x) / span_x * 100
        y = (max_y - point[1]) / span_y * 100
        return [round(x, 2), round(y, 2)]

    return [place(point) for point in points]


class RaceState:
    def __init__(self):
        self.drivers = {}
        self.lines = {}
        self.positions = {}
        self.session_info = {}
        self.track_raw = []
        self.driver_season = {}
        self.constructor_season = {}

    def set_season(self, driver_points, constructor_points):
        self.driver_season = dict(driver_points)
        self.constructor_season = dict(constructor_points)

    def apply(self, topic, data):
        if not isinstance(data, dict):
            return
        if topic == "DriverList":
            self.drivers = _merge(self.drivers, data)
        elif topic == "TimingData":
            lines = data.get("Lines") or {}
            self.lines = _merge(self.lines, lines)
        elif topic == "SessionInfo":
            self.session_info = _merge(self.session_info, data)
        elif topic == "Position.z":
            self._apply_positions(data)

    def _apply_positions(self, data):
        batches = data.get("Position") or []
        if isinstance(batches, dict):
            batches = [batches]
        for batch in batches:
            entries = batch.get("Entries") or {}
            for number, entry in entries.items():
                coords = _coords(entry)
                if coords is None:
                    continue
                self.positions[str(number)] = coords
                if not self.track_raw or _far_enough(self.track_raw[-1], coords):
                    self.track_raw.append(coords)
                    if len(self.track_raw) > 4000:
                        self.track_raw = self.track_raw[-4000:]

    def snapshot(self):
        kind = _session_kind(self.session_info)
        track_name, location = _track_title(self.session_info)
        cars = []
        for number, driver in self.drivers.items():
            if not isinstance(driver, dict):
                continue
            code = driver.get("Tla") or driver.get("RacingNumber") or str(number)
            line = self.lines.get(str(number)) or self.lines.get(number) or {}
            position_text = line.get("Position")
            try:
                position = int(position_text)
            except (TypeError, ValueError):
                position = None
            retired = bool(line.get("Retired")) or str(line.get("Status") or "").lower() in {"retired", "out"}
            team = _match_team(driver.get("TeamName") or "", self.constructor_season.keys())
            gap = line.get("GapToLeader") or ""
            if isinstance(gap, dict):
                gap = gap.get("Value") or ""
            if position == 1:
                gap = "LEAD"
            cars.append(
                {
                    "number": str(driver.get("RacingNumber") or number),
                    "code": code,
                    "name": driver.get("LastName") or driver.get("FullName") or code,
                    "team": team,
                    "color": driver.get("TeamColour") or "888888",
                    "position": position,
                    "retired": retired,
                    "gap": gap or ("—" if position != 1 else "LEAD"),
                }
            )

        classified = [car for car in cars if car["position"] is not None]
        classified.sort(key=lambda car: (car["retired"], car["position"], car["code"]))
        projected = project_standings(
            classified,
            self.driver_season,
            self.constructor_season,
            kind,
        )
        raw_points = list(self.track_raw) + [self.positions[number] for number in self.positions]
        normalized = _normalize(raw_points)
        track = normalized[: len(self.track_raw)]
        car_points = {
            number: normalized[len(self.track_raw) + index]
            for index, number in enumerate(self.positions)
        }

        def public_driver(row):
            return {
                "code": row["code"],
                "name": row["name"],
                "team": row["team"],
                "color": row["color"],
                "position": row["position"],
                "retired": row["retired"],
                "season": row["season"],
                "racePoints": row["race_points"],
                "projected": row["projected"],
            }

        constructors = [
            {
                "name": row["name"],
                "color": row["color"],
                "season": row["season"],
                "racePoints": row["race_points"],
                "projected": row["projected"],
                "drivers": [
                    {"code": item["code"], "racePoints": item["race_points"]}
                    for item in row["drivers"]
                ],
            }
            for row in projected["constructors"]
        ]

        map_cars = []
        for number, point in car_points.items():
            driver = self.drivers.get(number) or {}
            code = driver.get("Tla") or number
            map_cars.append(
                {
                    "code": code,
                    "color": driver.get("TeamColour") or "888888",
                    "x": point[0],
                    "y": point[1],
                }
            )

        return {
            "session": {
                "trackName": track_name,
                "location": location,
                "name": (self.session_info or {}).get("Name") or "",
                "kind": kind,
            },
            "raceOrder": [
                {
                    "code": car["code"],
                    "name": car["name"],
                    "team": car["team"],
                    "color": car["color"],
                    "position": car["position"],
                    "gap": car["gap"],
                    "retired": car["retired"],
                }
                for car in classified
            ],
            "drivers": [public_driver(row) for row in projected["drivers"]],
            "constructors": constructors,
            "cars": map_cars,
            "track": track,
        }


def _far_enough(previous, coords):
    dx = previous[0] - coords[0]
    dy = previous[1] - coords[1]
    return (dx * dx + dy * dy) > 4
