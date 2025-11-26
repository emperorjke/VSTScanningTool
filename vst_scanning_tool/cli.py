from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .normalizer import ManufacturerNormalizer
from .scanner import scan_paths
from .writer import write_text_report


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan VST2/VST3 plugins with deduplication and normalization.")
    parser.add_argument("paths", nargs="+", type=Path, help="Paths to scan for plugins")
    parser.add_argument("--output", "-o", type=Path, default=Path("plugins.txt"), help="Where to write the report")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv or [])
    normalizer = ManufacturerNormalizer()
    records = scan_paths(args.paths, normalizer=normalizer)
    write_text_report(records, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
