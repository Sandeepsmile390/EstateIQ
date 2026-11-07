"""Regenerate the current code-grounded generic IEEE-style manuscript PDF."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "research" / "ieee" / "build_ieee_paper.py"), run_name="__main__")
