from datetime import datetime, timezone


def parse_time(value):
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def latest_finished_race(sessions, now):
    finished = []
    for session in sessions:
        kind = session.get("session_name") or session.get("session_type")
        if kind != "Race":
            continue
        if parse_time(session["date_start"]) <= now:
            finished.append(session)
    if not finished:
        return None
    finished.sort(key=lambda session: session["date_start"])
    return finished[-1]


def latest_at(records, moment):
    chosen = None
    for record in records:
        if parse_time(record["date"]) <= moment:
            chosen = record
        else:
            break
    return chosen


def format_gap(position, gap):
    if position == 1 or gap in (0, 0.0, "0", "0.0"):
        return "LEAD"
    if gap is None or gap == "":
        return "—"
    if isinstance(gap, str):
        return gap
    return f"+{float(gap):.3f}"
