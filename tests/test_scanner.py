from __future__ import annotations

import json
import plistlib
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

from vst_scanning_tool import (
    ManufacturerNormalizer,
    discover_windows_plugin_paths,
    scan_paths,
)


def _write_vst3_plugin(root: Path, name: str, manufacturer: str, identifier: str) -> Path:
    bundle = root / f"{name}.vst3"
    info = bundle / "Contents" / "Info.plist"
    info.parent.mkdir(parents=True, exist_ok=True)
    with info.open("wb") as fh:
        plistlib.dump(
            {
                "CFBundleName": name,
                "CFBundleIdentifier": identifier,
                "AudioComponentManufacturer": manufacturer,
                "CFBundleShortVersionString": "1.0.0",
            },
            fh,
        )
    return bundle


def _write_vst2_plugin(root: Path, filename: str, manufacturer: str, plugin_name: str) -> Path:
    plugin = root / filename
    plugin.touch()
    sidecar = plugin.with_suffix(plugin.suffix + ".metadata.json")
    sidecar.write_text(
        json.dumps({"name": plugin_name, "manufacturer": manufacturer}),
        encoding="utf-8",
    )
    return plugin


class ScannerTests(unittest.TestCase):
    def test_vst3_metadata_and_normalization(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vst3 = _write_vst3_plugin(root, "smartEQ 2", "sonible", "com.sonible.smarteq")

            records = scan_paths([root])
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.plugin_type, "VST3")
            self.assertEqual(record.manufacturer, "Sonible")
            self.assertEqual(record.name, "smartEQ 2")
            self.assertEqual(record.identifier, "com.sonible.smarteq")
            self.assertEqual(record.version, "1.0.0")
            self.assertEqual(record.path, vst3)

    def test_deduplicates_duplicates(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vst3 = _write_vst3_plugin(root, "Gullfoss", "2CAudio", "com.soundtheory.gullfoss")
            duplicate = _write_vst3_plugin(root, "Gullfoss", "2CAudio", "com.soundtheory.gullfoss")

            records = scan_paths([vst3, duplicate])
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].name, "Gullfoss")
            self.assertEqual(records[0].manufacturer, "2CAudio")

    def test_bx_prefix_gets_brainworx(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plugin = _write_vst2_plugin(root, "bx_console.dll", "Plugin Alliance", "bx_console 9000")

            normalizer = ManufacturerNormalizer()
            records = scan_paths([plugin], normalizer=normalizer)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].manufacturer, "Brainworx (Plugin Alliance)")

    def test_sidecar_metadata_for_acustica(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_vst2_plugin(root, "Aquarius.dll", "acustica audio", "Aquarius")

            records = scan_paths([root])
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].manufacturer, "Acustica Audio")
            self.assertEqual(records[0].name, "Aquarius")


class WindowsPathDiscoveryTests(unittest.TestCase):
    def test_discovery_is_noop_on_non_windows(self):
        with mock.patch("vst_scanning_tool.windows_paths.sys.platform", "linux"):
            self.assertEqual(discover_windows_plugin_paths(), [])


if __name__ == "__main__":
    unittest.main()
