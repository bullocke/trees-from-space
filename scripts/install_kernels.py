"""Register the Trees from Space Jupyter kernels for the current user.

A Jupyter kernel starts the environment's interpreter directly, without the
activation scripts that normally set GDAL and PROJ data paths, so each kernel
spec written here carries those variables itself. ``PYTHONNOUSERSITE`` keeps
packages from ``~/.local`` out of the Python kernel, and ``R_LIBS_USER`` points
the R kernel at the environment's own library.

Usage (run with the environment's Python):

    <python-prefix>/bin/python scripts/install_kernels.py
    <python-prefix>/bin/python scripts/install_kernels.py --r-prefix <r-prefix>

Kernels appear as "Python 3.x (Trees from Space)" and "R 4.x (Trees from
Space)" in Jupyter, OnDemand, and VS Code. Remove one with
``jupyter kernelspec remove tfs-python``.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from jupyter_core.paths import jupyter_data_dir

LOG = logging.getLogger("install_kernels")
PYTHON_KERNEL = "tfs-python"
R_KERNEL = "tfs-r"


def geodata_env(prefix: Path) -> dict[str, str]:
    """Return GDAL and PROJ data paths that exist inside ``prefix``."""
    env = {}
    for name, sub in (("GDAL_DATA", "share/gdal"), ("PROJ_DATA", "share/proj")):
        path = prefix / sub
        if path.is_dir():
            env[name] = str(path)
        else:
            LOG.warning("%s not found in the environment; %s left unset", sub, name)
    return env


def python_spec(prefix: Path) -> dict:
    """Build the kernel spec for the Python environment at ``prefix``."""
    python = prefix / "bin" / "python"
    version = subprocess.run(
        [str(python), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "argv": [str(python), "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": f"Python {version} (Trees from Space)",
        "language": "python",
        "env": {"PYTHONNOUSERSITE": "1", **geodata_env(prefix)},
        "metadata": {"debugger": True},
    }


def r_spec(prefix: Path) -> tuple[dict, Path]:
    """Build the kernel spec for the R environment at ``prefix``.

    Starts from the spec that IRkernel ships, so its arguments track the
    installed IRkernel version, and makes the R path absolute.
    """
    shipped = prefix / "lib" / "R" / "library" / "IRkernel" / "kernelspec"
    spec = json.loads((shipped / "kernel.json").read_text())
    r_binary = prefix / "bin" / "R"
    spec["argv"][0] = str(r_binary)
    first_line = subprocess.run(
        [str(r_binary), "--version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    version = ".".join(first_line.split()[2].split(".")[:2])
    spec["display_name"] = f"R {version} (Trees from Space)"
    spec["env"] = {
        "R_LIBS_USER": str(prefix / "lib" / "R" / "library"),
        **geodata_env(prefix),
    }
    return spec, shipped


def write_spec(
    kernels_dir: Path, name: str, spec: dict, assets: Path | None = None
) -> Path:
    """Write ``spec`` (and any logo files) to ``kernels_dir/name``."""
    target = kernels_dir / name
    target.mkdir(parents=True, exist_ok=True)
    if assets is not None:
        for logo in assets.glob("logo-*"):
            shutil.copy2(logo, target / logo.name)
    (target / "kernel.json").write_text(json.dumps(spec, indent=1) + "\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--python-prefix",
        type=Path,
        default=Path(sys.prefix),
        help="Python environment prefix (default: the running interpreter's)",
    )
    parser.add_argument(
        "--r-prefix", type=Path, help="R environment prefix (skip R if omitted)"
    )
    parser.add_argument(
        "--kernels-dir",
        type=Path,
        default=Path(jupyter_data_dir()) / "kernels",
        help="Where to write kernel specs (default: the user's Jupyter data dir)",
    )
    parser.add_argument("--skip-python", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.skip_python:
        prefix = args.python_prefix.resolve()
        path = write_spec(args.kernels_dir, PYTHON_KERNEL, python_spec(prefix))
        LOG.info("Registered %s -> %s", PYTHON_KERNEL, path)
    if args.r_prefix is not None:
        spec, assets = r_spec(args.r_prefix.resolve())
        path = write_spec(args.kernels_dir, R_KERNEL, spec, assets)
        LOG.info("Registered %s -> %s", R_KERNEL, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
