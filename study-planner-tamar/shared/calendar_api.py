import json
import urllib.parse
import urllib.request
from datetime import date, timedelta

HEBCAL_URL = "https://www.hebcal.com/hebcal"


class CalendarError(Exception):
    pass


def fetch_holidays(start, end, opener=None):
    params = {"v": "1", "cfg": "json", "maj": "on", "i": "on",
              "start": start.isoformat(), "end": end.isoformat()}
    url = HEBCAL_URL + "?" + urllib.parse.urlencode(params)
    opener = opener or urllib.request.urlopen
    try:
        with opener(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise CalendarError(f"hebcal unavailable: {e}") from e
    if "items" not in data:
        raise CalendarError("hebcal returned no items")
    return data["items"]


def blocked_days(start, end, opener=None):
    items = fetch_holidays(start, end, opener)
    blocked = set()
    events = []
    for it in items:
        day = it["date"][:10]
        if it.get("yomtov"):
            blocked.add(day)
        events.append(f"{day} {it['title']}")
    d = start
    while d <= end:
        if d.weekday() == 5:
            blocked.add(d.isoformat())
        d += timedelta(days=1)
    return sorted(blocked), events
