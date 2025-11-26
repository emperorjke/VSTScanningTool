from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PluginRecord:
    """Represents a single plugin instance discovered during scanning."""

    name: str
    manufacturer: str
    plugin_type: str
    path: Path
    identifier: Optional[str] = None
    version: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        """Generate a stable key for deduplication."""
        normalized_name = _clean(self.name)
        normalized_manufacturer = _clean(self.manufacturer)
        normalized_type = self.plugin_type.upper()
        return normalized_type, normalized_manufacturer, normalized_name

    def merge(self, other: "PluginRecord") -> "PluginRecord":
        """Merge metadata from another record, preferring richer data."""
        if self.identifier is None and other.identifier:
            self.identifier = other.identifier
        if self.version is None and other.version:
            self.version = other.version

        # Prefer populated manufacturer/name info from the richer record.
        if _is_richer_text(other.manufacturer, self.manufacturer):
            self.manufacturer = other.manufacturer
        if _is_richer_text(other.name, self.name):
            self.name = other.name

        # Combine paths and auxiliary data.
        self.extra = {**other.extra, **self.extra}
        return self


def _clean(value: str) -> str:
    return value.strip().lower()


def _is_richer_text(candidate: str, current: str) -> bool:
    if not candidate:
        return False
    if not current:
        return True
    return len(candidate.strip()) > len(current.strip())
