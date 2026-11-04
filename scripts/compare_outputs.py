"""Compare the Python and R outputs of a lesson that writes a raster result.

Checks, in order: the same set of granules or STAC items was considered, the
same one was selected, the output rasters share CRS, transform, and shape,
their valid-pixel masks are identical, their values agree within a tolerance,
and the summary tables agree.

Usage:

    python scripts/compare_outputs.py outputs/hls-vegetation-map/python \
        outputs/hls-vegetation-map/r --record \
        tutorials/hls-vegetation-map/validation/2026-11-03-local-python-vs-r.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np
import rasterio

LOG = logging.getLogger("compare_outputs")
SUMMARY_FIELDS = (
    "aoi_pixels",
    "clear_land_pixels",
    "water_pixels",
    "masked_pixels",
    "no_data_pixels",
    "clear_fraction",
    "ndvi_median",
    "ndvi_p25",
    "ndvi_p75",
)


def considered(prov: dict) -> list[str]:
    """Granule IDs (HLS lessons) or STAC item IDs (STAC lessons) considered."""
    return sorted(prov.get("granules_considered") or prov.get("items_considered") or [])


def selected(prov: dict) -> str | None:
    """The granule or STAC item the lesson selected."""
    if "selected_granule" in prov:
        return prov["selected_granule"]["granule_id"]
    return prov.get("source_item", {}).get("id")


def single(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"expected one {pattern} in {folder}, found {len(matches)}")
    return matches[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("python_dir", type=Path)
    parser.add_argument("r_dir", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--record", type=Path, help="write the result as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    prov = {}
    rasters = {}
    summaries = {}
    for lang, folder in (("python", args.python_dir), ("r", args.r_dir)):
        prov_path = single(folder, "*_provenance.json")
        prov[lang] = json.loads(prov_path.read_text())
        with rasterio.open(single(folder, "*.tif")) as src:
            rasters[lang] = {
                "crs": src.crs,
                "transform": src.transform,
                "data": src.read(1).astype("float64"),
                "nodata": src.nodata,
            }
        with single(folder, "*_summary.csv").open() as handle:
            summaries[lang] = next(csv.DictReader(handle))

    py, r = rasters["python"], rasters["r"]
    for raster in (py, r):
        if raster["nodata"] is not None and not np.isnan(raster["nodata"]):
            raster["data"][raster["data"] == raster["nodata"]] = np.nan
    same_grid = (
        py["crs"] == r["crs"]
        and py["transform"] == r["transform"]
        and py["data"].shape == r["data"].shape
    )
    result = {
        "check": "python-vs-r",
        "same_granule_set": considered(prov["python"]) == considered(prov["r"]),
        "same_selected_granule": selected(prov["python"]) == selected(prov["r"]),
        "selected_granule": selected(prov["python"]),
        "same_grid": bool(same_grid),
        "nodata": {"python": py["nodata"], "r": r["nodata"]},
    }
    if same_grid:
        valid_py, valid_r = np.isfinite(py["data"]), np.isfinite(r["data"])
        both = valid_py & valid_r
        diff = np.abs(py["data"][both] - r["data"][both])
        result.update(
            {
                "identical_valid_masks": bool(np.array_equal(valid_py, valid_r)),
                "valid_pixels": int(both.sum()),
                "max_abs_diff": float(diff.max()) if diff.size else None,
                "pixels_above_tolerance": int((diff > args.tolerance).sum()),
            }
        )
    result["summary_differences"] = {
        field: [summaries["python"][field], summaries["r"][field]]
        for field in SUMMARY_FIELDS
        if not np.isclose(
            float(summaries["python"][field]), float(summaries["r"][field]), atol=1e-4
        )
    }
    result["tolerance"] = args.tolerance
    result["passed"] = bool(
        result["same_granule_set"]
        and result["same_selected_granule"]
        and same_grid
        and result.get("identical_valid_masks")
        and result.get("pixels_above_tolerance") == 0
        and not result["summary_differences"]
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
