import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter


def schedule_config(graph: dict) -> dict | None:
    start = next((node for node in graph.get("nodes", []) if node.get("type") == "start"), None)
    config = start.get("data", {}).get("config", {}) if start else {}
    schedule = config.get("schedule", {})
    if "schedule" not in config.get("triggers", []) or not schedule.get("enabled", True):
        return None
    return schedule


def next_schedule_at(graph: dict, after: datetime | None = None) -> datetime | None:
    schedule = schedule_config(graph)
    if not schedule:
        return None
    try:
        timezone = ZoneInfo(str(schedule.get("timezone", "UTC")))
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown schedule timezone") from exc
    base = (after or datetime.now(UTC)).astimezone(timezone)
    return croniter(str(schedule.get("cron", "")), base).get_next(datetime).astimezone(UTC)


def schedule_inputs(graph: dict) -> dict:
    schedule = schedule_config(graph) or {}
    raw = schedule.get("inputs_json", "{}")
    result = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(result, dict):
        raise ValueError("Scheduled inputs must be a JSON object")
    return result
