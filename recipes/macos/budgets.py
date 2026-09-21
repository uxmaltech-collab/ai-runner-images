"""Bound RPC envelopes around the selected recipes, including their child deadlines."""
import importlib.util
import math
from pathlib import Path

# Conservative transfer + extraction + verification allowance, not measured throughput.
STAGE_BYTES_PER_SECOND = 2 * 1024 * 1024
STAGE_OVERHEAD_SECONDS = 120
VERIFICATION_SECONDS = 300


def stage_budget(payload_bytes):
    return STAGE_OVERHEAD_SECONDS + math.ceil(payload_bytes / STAGE_BYTES_PER_SECOND)


def install_budget(profile, parent_layer):
    components = {'swiftlint': 300}
    if parent_layer == 'macos-xcode-maestro':
        components['agents'] = 300
    if profile == 'macos-flutter' and parent_layer != 'flutter-dart-ios':
        path = Path(__file__).resolve().parents[1] / 'flutter-dart/install.py'
        spec = importlib.util.spec_from_file_location('flutter_install_budget', path)
        recipe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recipe)
        components['flutter'] = recipe.INSTALL_TIMEOUT_SECONDS
    return {'component_seconds': components,
            'install_seconds': sum(components.values()) + VERIFICATION_SECONDS}
