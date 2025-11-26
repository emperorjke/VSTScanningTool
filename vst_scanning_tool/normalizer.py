from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class NormalizedIdentity:
    manufacturer: str
    plugin_name: str
    plugin_type: str


class ManufacturerNormalizer:
    """Normalizes manufacturer and plugin names to reduce duplicates."""

    def __init__(self, extra_aliases: Optional[Dict[str, str]] = None) -> None:
        aliases = {
            "sonible": "Sonible",
            "sonible gmbh": "Sonible",
            "plugin alliance": "Plugin Alliance",
            "brainworx": "Brainworx (Plugin Alliance)",
            "bx": "Brainworx (Plugin Alliance)",
            "2caudio": "2CAudio",
            "acustica": "Acustica Audio",
            "acustica audio": "Acustica Audio",
            "u-he": "u-he",
            "softube": "Softube",
            "iZotope": "iZotope",
        }
        self.aliases: Dict[str, str] = {k.lower(): v for k, v in aliases.items()}
        if extra_aliases:
            self.aliases.update({k.lower(): v for k, v in extra_aliases.items()})

    def normalize_manufacturer(self, manufacturer: str, plugin_name: Optional[str] = None) -> str:
        candidate = (manufacturer or "").strip()
        lowered = candidate.lower()

        # Heuristics based on plugin naming conventions.
        if plugin_name:
            if plugin_name.lower().startswith("bx_"):
                return "Brainworx (Plugin Alliance)"
            if "sonible" in plugin_name.lower():
                return "Sonible"

        if lowered in self.aliases:
            return self.aliases[lowered]

        # Attempt to split on known separators to salvage a meaningful name.
        for token in re.split(r"[\s|/-]+", candidate):
            token_lower = token.lower()
            if token_lower in self.aliases:
                return self.aliases[token_lower]

        return candidate or "Unknown"

    def normalize_plugin_name(self, plugin_name: str) -> str:
        plugin_name = plugin_name.strip()
        cleaned = re.sub(r"\s+", " ", plugin_name)
        cleaned = re.sub(r"[_-]+", " ", cleaned)
        cleaned = cleaned.replace("®", "").strip()
        return cleaned or "Unknown Plugin"

    def identity(self, manufacturer: str, plugin_name: str, plugin_type: str) -> NormalizedIdentity:
        normalized_manufacturer = self.normalize_manufacturer(manufacturer, plugin_name)
        normalized_name = self.normalize_plugin_name(plugin_name)
        return NormalizedIdentity(
            manufacturer=normalized_manufacturer,
            plugin_name=normalized_name,
            plugin_type=plugin_type.upper(),
        )

    def deduplicate(self, records: Iterable["PluginRecord"]):
        from .models import PluginRecord

        deduped: Dict[tuple[str, str, str], PluginRecord] = {}
        for record in records:
            identity = self.identity(record.manufacturer, record.name, record.plugin_type)
            record.manufacturer = identity.manufacturer
            record.name = identity.plugin_name
            record.plugin_type = identity.plugin_type
            key = (identity.plugin_type, identity.manufacturer.lower(), identity.plugin_name.lower())
            if key not in deduped:
                deduped[key] = record
            else:
                deduped[key].merge(record)
        return list(deduped.values())
