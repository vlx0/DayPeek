"""Счётчики за сегодня, без настоящего журнала."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from daypeek.log import parse_payload
from daypeek.today import Event, build_day, is_plug_device, parse_iso

TZ = timezone(timedelta(hours=5))


def at(month: int, day: int, hour: int) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=TZ)


class ParseTests(unittest.TestCase):
    def test_iso_and_payload(self) -> None:
        when = parse_iso("2026-11-01T10:15:00.3877700+05:00")
        self.assertIsNotNone(when)
        self.assertEqual(when.day, 1)
        naive = parse_iso("2026-11-01T10:15:00")
        self.assertIsNotNone(naive)
        self.assertIsNotNone(naive.tzinfo)
        with self.assertRaises(Exception):
            parse_payload("ERR отказано в доступе")

    def test_usb_filter(self) -> None:
        self.assertTrue(is_plug_device(r"USB\VID_04E8&PID_6860\ABC"))
        self.assertFalse(is_plug_device(r"USB\ROOT_HUB30\4&1dd9c07d&0&0"))
        self.assertFalse(is_plug_device(r"PCI\VEN_10DE&DEV_2504\4&x"))


class DayTests(unittest.TestCase):
    def test_counts_only_today(self) -> None:
        now = at(11, 1, 12)
        events = [
            Event(at(11, 1, 8), "boot", 12, ()),
            Event(at(11, 1, 9), "wake", 1, ()),
            Event(at(11, 1, 9), "crash", 1000, ()),
            Event(at(11, 1, 10), "usb", 400, (r"USB\VID_0951&PID_1665\60A44C413CA0BF6059760336",)),
            Event(at(11, 1, 10), "usb", 400, (
                r"USBSTOR\Disk&Ven_Kingston&Prod_DataTraveler_2.0\60A44C413CA0BF6059760336&0",
            )),
            Event(at(11, 1, 10), "usb", 400, (r"USB\ROOT_HUB30\x",)),
            Event(at(11, 1, 11), "soft", 1033, ()),
            Event(at(10, 31, 23), "boot", 12, ()),
        ]
        day = build_day(events, now)
        self.assertEqual(day.boots, 1)
        self.assertEqual(day.wakes, 1)
        self.assertEqual(day.crashes, 1)
        self.assertEqual(day.plugs, 1)
        self.assertEqual(day.softs, 1)


if __name__ == "__main__":
    unittest.main()
