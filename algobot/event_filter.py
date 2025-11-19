"""Simple external event filter placeholder."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from config.settings import Settings


@dataclass
class MacroEvent:
    name: str
    start_time: datetime
    end_time: datetime
    impact: str


class ExternalEventFilter:
    """Checks calendared macro events to pause trading."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.events: List[MacroEvent] = []

    def load_events(self, events: List[MacroEvent]) -> None:
        """Load events from an external calendar or API."""

        self.events = events

    def should_halt(self, now: datetime) -> bool:
        """Return True if trading should pause due to macro event."""

        for event in self.events:
            if event.start_time <= now <= event.end_time:
                return True
        return False

    def load_from_file(self, file_path: Path) -> None:
        """Load macro events from a JSON file."""

        if not file_path.exists():
            return
        raw = json.loads(file_path.read_text())
        events: List[MacroEvent] = []
        for item in raw:
            events.append(
                MacroEvent(
                    name=item["name"],
                    start_time=datetime.fromisoformat(item["start_time"]),
                    end_time=datetime.fromisoformat(item["end_time"]),
                    impact=item.get("impact", "high"),
                )
            )
        self.events = events


__all__ = ["MacroEvent", "ExternalEventFilter"]
