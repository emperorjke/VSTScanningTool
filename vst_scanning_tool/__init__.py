from .models import PluginRecord
from .normalizer import ManufacturerNormalizer
from .scanner import scan_paths
from .writer import write_text_report
from .windows_paths import discover_windows_plugin_paths

__all__ = [
    "ManufacturerNormalizer",
    "PluginRecord",
    "scan_paths",
    "discover_windows_plugin_paths",
    "write_text_report",
]
