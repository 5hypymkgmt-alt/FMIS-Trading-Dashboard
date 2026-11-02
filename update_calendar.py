import os
import json
from urllib.request import Request, urlopen

API_URL = (
    "https://www.financecalendar.com/wp-json/fc/v1/calendar"
    "?country=US,GB&impact=high&limit=100"
)
)

def fetch_calendar():
    api_key = os.environ.get("FINANCECALENDAR_API_KEY")

    if not api_key:
        raise RuntimeError("FinanceCalendar API key is missing")

    request = Request(
        API_URL,
        headers={"X-API-Key": api_key}
    )

    with urlopen(request, timeout=30) as response:
        return json.load(response)

def validate_calendar(data):
    if not isinstance(data, dict):
        raise ValueError("Calendar response must be an object")

    events = data.get("events")

    if not isinstance(events, list):
        raise ValueError("Calendar response has no valid events list")

    valid_events = []

    for event in events:
        if not isinstance(event, dict):
            continue

        if event.get("country") not in ("US", "GB"):
            continue

        if event.get("impact") != "high":
            continue

        if event.get("status") == "cancelled":
            continue

        if not event.get("title") and not event.get("name"):
            continue

        valid_events.append(event)

    return valid_events

from pathlib import Path
from datetime import datetime, timezone
import tempfile

OUTPUT_FILE = Path(__file__).resolve().parent / "calendar-data.json"

def save_calendar(events):
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "FinanceCalendar",
        "events": events
    }

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=OUTPUT_FILE.parent,
            prefix=".calendar-",
            suffix=".tmp",
            delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, indent=2)
            temporary.write("\n")

        temporary_path.replace(OUTPUT_FILE)

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

def main():
    print("Connecting to FinanceCalendar...")
    data = fetch_calendar()
    events = validate_calendar(data)
    save_calendar(events)
    print("Calendar updated successfully")
    print("High-impact events:", len(events))


if __name__ == "__main__":
    main()
