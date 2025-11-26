from __future__ import annotations

import json
import plistlib
from pathlib import Path
from typing import Iterable, List, Optional

from .models import PluginRecord
from .normalizer import ManufacturerNormalizer

SUPPORTED_EXTENSIONS = {".vst3", ".vst", ".dll"}


def scan_paths(paths: Iterable[Path], *, normalizer: Optional[ManufacturerNormalizer] = None) -> List[PluginRecord]:
    """Scan directories/files and return a list of PluginRecord entries."""

    normalizer = normalizer or ManufacturerNormalizer()
    records: List[PluginRecord] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                record = _inspect_plugin(path)
                if record:
                    records.append(record)
            for candidate in path.rglob("*"):
                if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                    record = _inspect_plugin(candidate)
                    if record:
                        records.append(record)
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            record = _inspect_plugin(path)
            if record:
                records.append(record)
    return normalizer.deduplicate(records)


def _inspect_plugin(path: Path) -> Optional[PluginRecord]:
    suffix = path.suffix.lower()
    plugin_type = "VST3" if suffix == ".vst3" else "VST2"

    if suffix == ".vst3" and path.is_dir():
        metadata = _read_vst3_metadata(path)
    else:
        metadata = _read_sidecar_metadata(path)

    name = metadata.get("name") or path.stem
    manufacturer = metadata.get("manufacturer") or path.parent.name
    identifier = metadata.get("identifier")
    version = metadata.get("version")

    return PluginRecord(
        name=name,
        manufacturer=manufacturer,
        plugin_type=plugin_type,
        path=path,
        identifier=identifier,
        version=version,
        extra=metadata,
    )


def _read_vst3_metadata(path: Path) -> dict:
    metadata: dict = {}
    info_plist = path / "Contents" / "Info.plist"
    if info_plist.exists():
        try:
            with info_plist.open("rb") as fh:
                plist_data = plistlib.load(fh)
            metadata.update({
                "name": plist_data.get("CFBundleName") or plist_data.get("CFBundleDisplayName"),
                "identifier": plist_data.get("CFBundleIdentifier"),
                "manufacturer": plist_data.get("AudioComponentManufacturer") or plist_data.get("Manufacturer"),
                "version": plist_data.get("CFBundleShortVersionString"),
            })
        except Exception:
            # If parsing fails, we fallback to filename-derived metadata.
            pass
    return metadata


def _read_sidecar_metadata(path: Path) -> dict:
    """Try to read JSON metadata placed next to the plugin binary."""

    metadata: dict = {}
    for suffix in (".metadata.json", ".json"):
        candidate = path.with_suffix(path.suffix + suffix)
        if candidate.exists():
            try:
                with candidate.open("r", encoding="utf-8") as fh:
                    metadata = json.load(fh)
                break
            except Exception:
                continue
    return metadata
