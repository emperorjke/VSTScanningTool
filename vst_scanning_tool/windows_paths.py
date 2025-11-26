from __future__ import annotations

"""Helpers for discovering Windows VST installation paths."""

import os
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple

# Default locations collected from the original VSTSCAN script.
WINDOWS_VST2_PATHS: Tuple[Path, ...] = (
    Path(r"C:\\Program Files\\Common Files\\Steinberg\\VST2"),
    Path(r"C:\\Program Files (x86)\\VstPlugins"),
    Path(r"C:\\Program Files (x86)\\Steinberg\\VstPlugins"),
    Path(os.path.expandvars(r"%USERPROFILE%\\Documents\\VST")),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\VST")),
)

WINDOWS_VST3_STANDARD_PATHS: Tuple[Path, ...] = (
    Path(r"C:\\Program Files\\Common Files\\VST3"),
    Path(r"C:\\Program Files (x86)\\Common Files\\VST3"),
)

WINDOWS_VST3_USER_PATHS: Tuple[Path, ...] = (
    Path(os.path.expandvars(r"%USERPROFILE%\\Documents\\VST3")),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\VST3")),
    Path(os.path.expandvars(r"%APPDATA%\\VST3")),
)

REGISTRY_LOCATIONS: Tuple[Tuple[str, str], ...] = (
    (r"SOFTWARE\\VST", "VSTPluginsPath"),
    (r"SOFTWARE\\Steinberg\\VST Plugins Path", "VSTPluginsPath"),
)


def _read_registry_paths(key_path: str, value_name: str = "VSTPluginsPath") -> List[Path]:
    """Read VST paths from the Windows registry.

    On non-Windows systems (or if ``winreg`` is unavailable) this safely returns
    an empty list so the caller can fall back to user-provided paths.
    """

    try:
        import winreg  # type: ignore
    except ImportError:
        return []

    locations: List[Path] = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, key_path) as key:
                raw_value, _ = winreg.QueryValueEx(key, value_name)
                for fragment in str(raw_value).split(";"):
                    fragment = fragment.strip()
                    if fragment:
                        locations.append(Path(fragment))
        except OSError:
            # Missing registry keys are normal on some systems.
            continue
    return locations


def _collect_existing_paths(paths: Iterable[Path]) -> Set[Path]:
    existing: Set[Path] = set()
    for path in paths:
        expanded = Path(os.path.expandvars(str(path)))
        if expanded.exists():
            existing.add(expanded)
    return existing


def discover_windows_plugin_paths() -> List[Path]:
    """Return unique, existing Windows plugin directories.

    The discovery process mirrors the behaviour of ``vstscan.py``: built-in
    defaults for VST2/VST3, user-specific VST3 locations, registry overrides for
    VST2, and manufacturer subdirectories under the standard VST3 folder. All
    returned paths are guaranteed to exist to avoid noisy errors during scans.
    """

    if not sys.platform.startswith("win"):
        return []

    discovered: Set[Path] = set()

    # VST3 defaults (including per-user paths).
    vst3_bases = _collect_existing_paths(
        list(WINDOWS_VST3_STANDARD_PATHS) + list(WINDOWS_VST3_USER_PATHS)
    )
    discovered.update(vst3_bases)

    # Manufacturer subfolders inside the standard Program Files VST3 directory.
    for base in WINDOWS_VST3_STANDARD_PATHS:
        expanded = Path(os.path.expandvars(str(base)))
        if expanded.exists():
            for child in expanded.iterdir():
                if child.is_dir():
                    discovered.add(child)

    # VST2 defaults and registry-defined plugin folders.
    vst2_candidates: Set[Path] = set(WINDOWS_VST2_PATHS)
    for key_path, value_name in REGISTRY_LOCATIONS:
        vst2_candidates.update(_read_registry_paths(key_path, value_name))
    discovered.update(_collect_existing_paths(vst2_candidates))

    return sorted(discovered)

