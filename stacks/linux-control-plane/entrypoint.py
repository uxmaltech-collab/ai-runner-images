"""Load the declared webhook file only into the control-plane process."""
import os
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).parent / "runners/control-plane"))
from runner_control_plane.profile import ENV_PREFIX

webhook_file = os.environ.get(f"{ENV_PREFIX}_WEBHOOK_SECRET_FILE")
if webhook_file:
    os.environ[f"{ENV_PREFIX}_WEBHOOK_SECRET"] = Path(webhook_file).read_text().strip()
runpy.run_module("app", run_name="__main__")
