"""Smoke-Test fuer den tatsaechlichen Programmeinstieg."""

import subprocess
import sys
from pathlib import Path


def test_entrypoint() -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(project_root / "main.py")],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Tender Research Agent" in result.stdout
    assert result.stderr == ""
