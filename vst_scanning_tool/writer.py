from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import PluginRecord


def write_text_report(records: Iterable[PluginRecord], output_path: Path) -> None:
    """Write a human-friendly txt report grouped by manufacturer."""

    grouped = {}
    for record in records:
        grouped.setdefault(record.manufacturer, []).append(record)

    lines = []
    for manufacturer in sorted(grouped.keys()):
        lines.append(f"[{manufacturer}]")
        for record in sorted(grouped[manufacturer], key=lambda r: (r.name.lower(), r.plugin_type)):
            version = f" v{record.version}" if record.version else ""
            lines.append(f"- {record.name} ({record.plugin_type}){version} :: {record.path}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
