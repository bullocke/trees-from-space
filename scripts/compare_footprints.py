"""Compare the Python and R outputs of a lesson that writes GEDI footprints.

Checks, in order: the same granules were considered and subset files came back
for the same granules (Harmony's work-item prefixes differ between jobs); the footprint GeoPackages hold the same footprints (matched by shot
number) with identical positions, heights, quality fields, and `kept` flags,
and times that agree within a millisecond; and the summary and screening
tables agree.

Usage:

    python scripts/compare_footprints.py outputs/gedi-canopy-height/python \
        outputs/gedi-canopy-height/r --record \
        tutorials/gedi-canopy-height/validation/2026-11-04-local-python-vs-r.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

LOG = logging.getLogger("compare_footprints")
EXACT_COLUMNS = (
    "granule",
    "beam",
    "beam_type",
    "lon",
    "lat",
    "quality_flag",
    "degrade_flag",
    "sensitivity",
    "solar_elevation_deg",
    "leaf_off_flag",
    "landsat_treecover_pct",
    "kept",
)


def single(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"expected one {pattern} in {folder}, found {len(matches)}")
    return matches[0]


def subset_granules(prov: dict) -> list[str]:
    """Granules with a subset file, without Harmony's work-item prefix."""
    return sorted(name.split("_", 1)[1] for name in prov["harmony"]["subset_files"])


def read_footprints(folder: Path) -> pd.DataFrame:
    """Read a footprint GeoPackage, indexed by shot number."""
    table = gpd.read_file(single(folder, "*_footprints.gpkg"))
    table["shot_number"] = table["shot_number"].astype(str)
    table["time_utc"] = pd.to_datetime(table["time_utc"], utc=True, format="ISO8601")
    table["kept"] = table["kept"].astype(bool)
    return table.set_index("shot_number").sort_index()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("python_dir", type=Path)
    parser.add_argument("r_dir", type=Path)
    parser.add_argument("--record", type=Path, help="write the result as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    folders = {"python": args.python_dir, "r": args.r_dir}
    prov = {
        lang: json.loads(single(folder, "*_provenance.json").read_text())
        for lang, folder in folders.items()
    }
    tables = {lang: read_footprints(folder) for lang, folder in folders.items()}
    py, r = tables["python"], tables["r"]
    rh_column = next(c for c in py.columns if c.startswith("rh") and c.endswith("_m"))

    same_shots = py.index.equals(r.index)
    result = {
        "check": "python-vs-r-footprints",
        "same_granule_set": sorted(prov["python"]["granules"])
        == sorted(prov["r"]["granules"]),
        "same_subset_granules": subset_granules(prov["python"])
        == subset_granules(prov["r"]),
        "footprints": {"python": len(py), "r": len(r)},
        "same_shot_numbers": bool(same_shots),
        "unique_shot_numbers": bool(py.index.is_unique and r.index.is_unique),
    }
    if same_shots:
        identical = {}
        for column in (*EXACT_COLUMNS, rh_column):
            a, b = py[column].to_numpy(), r[column].to_numpy()
            if a.dtype.kind in "fc" or b.dtype.kind in "fc":
                same = np.array_equal(a.astype(float), b.astype(float), equal_nan=True)
            else:
                same = np.array_equal(a.astype(str), b.astype(str))
            identical[column] = bool(same)
        time_diff = (py["time_utc"] - r["time_utc"]).abs().dt.total_seconds()
        result["identical_columns"] = identical
        result["max_time_difference_s"] = float(time_diff.max())
        result["same_geometry"] = bool(
            py.geometry.geom_equals_exact(r.geometry, 0).all()
        )

    summaries = {
        lang: pd.read_csv(single(folder, "*_summary.csv")).iloc[0]
        for lang, folder in folders.items()
    }
    result["summary_differences"] = {
        field: [str(summaries["python"][field]), str(summaries["r"][field])]
        for field in summaries["python"].index
        if str(summaries["python"][field]) != str(summaries["r"][field])
        and not (
            pd.api.types.is_number(summaries["python"][field])
            and np.isclose(
                float(summaries["python"][field]), float(summaries["r"][field])
            )
        )
    }
    screenings = {
        lang: pd.read_csv(single(folder, "*_screening.csv"))
        for lang, folder in folders.items()
    }
    result["same_screening_table"] = bool(screenings["python"].equals(screenings["r"]))
    result["passed"] = bool(
        result["same_granule_set"]
        and result["same_subset_granules"]
        and same_shots
        and result["unique_shot_numbers"]
        and all(result["identical_columns"].values())
        and result["max_time_difference_s"] < 1e-3
        and result["same_geometry"]
        and not result["summary_differences"]
        and result["same_screening_table"]
    )
    text = json.dumps(result, indent=1)
    print(text)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(text + "\n")
        LOG.info("Recorded %s", args.record)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
