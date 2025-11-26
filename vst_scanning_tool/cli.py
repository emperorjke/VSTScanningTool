from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .normalizer import ManufacturerNormalizer
from .scanner import scan_paths
from .writer import write_text_report


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan VST2/VST3 plugins with deduplication and normalization.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Paths to scan for plugins. If omitted on Windows, default VST paths are used.",
    )
    parser.add_argument("--output", "-o", type=Path, default=Path("plugins.txt"), help="Where to write the report")
    parser.add_argument(
        "--include-default-windows-paths",
        action="store_true",
        help="Also scan standard Windows VST locations in addition to any provided paths.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv or [])
    from .windows_paths import discover_windows_plugin_paths

    discovered: List[Path] = []
    if not args.paths or args.include_default_windows_paths:
        discovered = discover_windows_plugin_paths()

    targets = list(args.paths) + discovered
    if not targets:
        raise SystemExit("No plugin paths were provided and no default Windows paths were found.")

    normalizer = ManufacturerNormalizer()
    records = scan_paths(targets, normalizer=normalizer)
    write_text_report(records, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
