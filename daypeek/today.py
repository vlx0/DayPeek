"""Счётчики за сегодня из уже прочитанных событий."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_FRAC = re.compile(r"(\.\d{6})\d+")
_SKIP_PREFIX = (
    "PCI\\",
    "DISPLAY\\",
    "ACPI\\",
    "ROOT\\",
    "HTREE\\",
    "STORAGE\\VOLUME",
    "SWD\\XVDD",
    "SWD\\WINTUN",
)

_MONTHS = "янв фев мар апр май июн июл авг сен окт ноя дек".split()


@dataclass
class Event:
    when: datetime
    kind: str
    id: int
    props: tuple[str, ...]


@dataclass
class Day:
    when: datetime
    boots: int
    wakes: int
    crashes: int
    plugs: int
    softs: int


def clean_text(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf").strip()


def parse_iso(text: str) -> datetime | None:
    raw = clean_text(str(text)).replace("Z", "+00:00")
    if not raw:
        return None
    raw = _FRAC.sub(r"\1", raw)
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return moment


def is_plug_device(instance: str) -> bool:
    raw = clean_text(instance)
    upper = raw.upper()
    if "&MI_" in upper or "ROOT_HUB" in upper or "VID_0000" in upper:
        return False
    if any(upper.startswith(prefix) for prefix in _SKIP_PREFIX):
        return False
    return "USB" in upper or upper.startswith("HID\\VID_")


_NEAR = timedelta(seconds=3)


def _local_day(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment
    return moment.astimezone()


def _stamp(moment: datetime) -> datetime:
    local = _local_day(moment)
    if local.tzinfo is None:
        local = local.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return local.astimezone(timezone.utc)


def _plug_key(instance: str) -> str:
    raw = clean_text(instance)
    if not raw:
        return ""
    bits = [bit for bit in raw.replace("\\", "#").split("#") if bit]
    junk = ("USBSTOR", "DISK", "VOLUME", "WPDBUSENUM", "VID_", "PID_")
    for bit in reversed(bits):
        cand = bit.split("&")[0].strip("_?")
        upper = cand.upper()
        if cand and len(cand) >= 4 and not any(token in upper for token in junk):
            return cand.upper()
    last = bits[-1] if bits else raw
    if last.upper().startswith("5&"):
        return raw.upper()
    cand = last.split("&")[0]
    return cand.upper() if cand else raw.upper()


def from_rows(rows: list[dict], now: datetime) -> list[Event]:
    events: list[Event] = []
    for row in rows:
        when = parse_iso(str(row.get("t") or ""))
        if when is None:
            continue
        kind = str(row.get("k") or "")
        try:
            number = int(row.get("id") or 0)
        except (TypeError, ValueError):
            number = 0
        props = row.get("p") or []
        if isinstance(props, str):
            props = [props]
        elif not isinstance(props, list):
            props = []
        events.append(Event(when, kind, number, tuple(str(item) for item in props)))
    return events


def build_day(events: list[Event], now: datetime) -> Day:
    today = _local_day(now).date()
    boots = wakes = crashes = plugs = softs = 0
    seen_usb: list[tuple[str, datetime]] = []
    for item in events:
        if _local_day(item.when).date() != today:
            continue
        if item.kind == "boot":
            boots += 1
        elif item.kind == "wake":
            wakes += 1
        elif item.kind == "crash":
            crashes += 1
        elif item.kind == "usb":
            instance = item.props[0] if item.props else ""
            if not is_plug_device(instance):
                continue
            key = _plug_key(instance)
            stamp = _stamp(item.when)
            skip = False
            for other_key, other_when in seen_usb:
                if other_key == key and abs((stamp - other_when).total_seconds()) <= _NEAR.total_seconds():
                    skip = True
                    break
            if skip:
                continue
            seen_usb.append((key, stamp))
            plugs += 1
        elif item.kind == "soft":
            softs += 1
    return Day(when=now, boots=boots, wakes=wakes, crashes=crashes, plugs=plugs, softs=softs)


def format_day(moment: datetime) -> str:
    local = _local_day(moment)
    return f"{local.day} {_MONTHS[local.month - 1]} {local.year}"
