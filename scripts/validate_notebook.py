"""Run a lesson notebook from a fresh kernel and record a validation result.

The runner executes the notebook with papermill, measures wall time, the peak
memory of the kernel process, and the bytes added to the cache, and reads the
JSON summary that each lesson prints in its final cell. With ``--record`` it
writes the result to ``tutorials/<topic>/validation/``. Hostnames, user names,
and home-directory paths are removed before anything is written or printed.

Examples:

    NB=tutorials/hls-vegetation-map/hls-vegetation-map-python.ipynb
    # Cold run (empty cache), then a warm rerun, then an offline rerun
    python scripts/validate_notebook.py $NB --label cold --record
    python scripts/validate_notebook.py $NB --label warm --record
    python scripts/validate_notebook.py $NB --label offline --offline --record

    # Override a setting from the notebook's parameters cell
    python scripts/validate_notebook.py $NB -p MAX_GRANULES 5
"""

from __future__ import annotations

import argparse
import ast
import getpass
import json
import logging
import os
import re
import resource
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import papermill

LOG = logging.getLogger("validate_notebook")
REPO = Path(__file__).resolve().parents[1]


@dataclass
class ValidationRecord:
    """One execution of one notebook on one platform."""

    notebook: str
    language: str
    platform: str
    label: str
    run_utc: str
    outcome: str
    wall_time_s: float
    peak_kernel_rss_mb: float
    new_cache_mb: float
    new_cache_files: int
    kernel: str
    commit: str
    parameters: dict = field(default_factory=dict)
    error: str | None = None
    summary: dict | None = None


def detect_platform() -> str:
    """Name the kind of machine (never its hostname)."""
    if "google.colab" in sys.modules:
        return "colab"
    on_chpc = (
        "chpc.utah.edu" in socket.getfqdn() or Path("/scratch/general/vast").is_dir()
    )
    if not on_chpc:
        return "local"
    if socket.gethostname().startswith("frisco"):
        return "chpc-frisco"
    partition = os.environ.get("SLURM_JOB_PARTITION")
    return f"chpc-{partition}" if partition else "chpc-login"


def cache_dir() -> Path:
    return Path(os.environ.get("TFS_CACHE_DIR", REPO / "cache"))


def cache_inventory(root: Path) -> dict[str, int]:
    """Map each cached file to its size in bytes."""
    if not root.exists():
        return {}
    return {str(p): p.stat().st_size for p in root.rglob("*") if p.is_file()}


def git_commit() -> str:
    """Return the short commit hash, marked '-dirty' if tracked files changed."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{sha}-dirty" if dirty else sha


def scrub(text: str) -> str:
    """Remove the home directory, user name, and hostname from ``text``."""
    replacements = [(str(Path.home()), "~")]
    user = getpass.getuser()
    host = socket.gethostname()
    for value, placeholder in ((host, "<host>"), (user, "<user>")):
        if value and len(value) > 2:
            replacements.append((value, placeholder))
    for value, placeholder in replacements:
        text = text.replace(value, placeholder)
    return text


def scrub_obj(obj):
    """Apply :func:`scrub` to every string inside a JSON-like object."""
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_obj(v) for v in obj]
    return obj


def final_summary(executed: Path) -> dict | None:
    """Parse the JSON object printed last by the notebook's final code cell."""
    cells = json.loads(executed.read_text())["cells"]
    code_cells = [c for c in cells if c["cell_type"] == "code" and c.get("outputs")]
    if not code_cells:
        return None
    text = "".join(
        "".join(o.get("text", "")) for o in code_cells[-1]["outputs"] if "text" in o
    )
    match = re.search(r"^\{.*\}\s*$", text, flags=re.S | re.M)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def notebook_language(path: Path) -> str:
    meta = json.loads(path.read_text()).get("metadata", {})
    return meta.get("kernelspec", {}).get("language", "python").lower()


def parse_value(raw: str):
    """Interpret a command-line parameter as a Python literal when possible."""
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--kernel", help="kernel name (default: tfs-python / tfs-r)")
    parser.add_argument("--label", default="run", help="e.g. cold, warm, offline")
    parser.add_argument("--platform", default=None, help="override platform name")
    parser.add_argument(
        "--offline", action="store_true", help="set TFS_OFFLINE=1 for the run"
    )
    parser.add_argument(
        "-p",
        "--parameter",
        nargs=2,
        action="append",
        default=[],
        metavar=("NAME", "VALUE"),
    )
    parser.add_argument(
        "--record", action="store_true", help="write the record to validation/"
    )
    parser.add_argument(
        "--executed-dir",
        type=Path,
        default=REPO / "logs" / "notebooks",
        help="where to keep the executed copy (ignored by git)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    notebook = args.notebook.resolve()
    language = "r" if notebook_language(notebook) == "r" else "python"
    kernel = args.kernel or ("tfs-r" if language == "r" else "tfs-python")
    platform_name = args.platform or detect_platform()
    parameters = {name: parse_value(value) for name, value in args.parameter}
    if args.offline:
        os.environ["TFS_OFFLINE"] = "1"
    os.environ.setdefault("MPLBACKEND", "Agg")

    stamp = datetime.now(UTC)
    args.executed_dir.mkdir(parents=True, exist_ok=True)
    executed = args.executed_dir / (
        f"{notebook.stem}-{platform_name}-{args.label}-{stamp:%Y%m%dT%H%M%S}.ipynb"
    )
    before = cache_inventory(cache_dir())
    start = time.monotonic()
    error = None
    try:
        papermill.execute_notebook(
            str(notebook),
            str(executed),
            parameters=parameters,
            kernel_name=kernel,
            cwd=str(notebook.parent),
            progress_bar=False,
        )
    except Exception as exc:  # papermill re-raises the failing cell's error
        error = f"{type(exc).__name__}: {str(exc).strip().splitlines()[-1][:300]}"
    wall = time.monotonic() - start
    after = cache_inventory(cache_dir())
    added = {k: v for k, v in after.items() if before.get(k) != v}

    record = ValidationRecord(
        notebook=str(notebook.relative_to(REPO)),
        language=language,
        platform=platform_name,
        label=args.label,
        run_utc=stamp.isoformat(timespec="seconds"),
        outcome="failed" if error else "passed",
        wall_time_s=round(wall, 1),
        # ru_maxrss is in kilobytes on Linux; it covers the kernel process.
        peak_kernel_rss_mb=round(
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1
        ),
        new_cache_mb=round(sum(added.values()) / 1e6, 3),
        new_cache_files=len(added),
        kernel=kernel,
        commit=git_commit(),
        parameters=parameters,
        error=error,
        summary=final_summary(executed) if executed.exists() else None,
    )
    result = scrub_obj(asdict(record))
    text = json.dumps(result, indent=1)
    print(text)
    if args.record:
        topic_dir = notebook.parent
        out = (
            topic_dir
            / "validation"
            / (f"{stamp:%Y-%m-%d}-{platform_name}-{language}-{args.label}.json")
        )
        out.parent.mkdir(exist_ok=True)
        out.write_text(text + "\n")
        LOG.info("Recorded %s", out.relative_to(REPO))
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
