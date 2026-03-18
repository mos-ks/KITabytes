from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_uv_project_metadata_and_runtime_are_available() -> None:
    assert (ROOT / "pyproject.toml").exists()
    assert (ROOT / "uv.lock").exists()

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import sys; sys.path.insert(0, 'backend'); import app.main; print(app.main.app.title)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "TestSense API"
