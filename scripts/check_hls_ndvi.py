"""Check an HLS lesson's NDVI output against independent calculations.

Two checks, both independent of the lesson's own windowing and metadata code:

1. Known pixels. For the window center and a few random clear pixels, read the
   raw stored values from the full remote red and near-infrared files at the
   pixel's map coordinates, scale them with the documented factor (0.0001), and
   compute NDVI by hand. A scaling error would show up in the reflectance
   values, which the check also reports, even where NDVI agrees.
2. NASA's HLS vegetation-index product (HLSL30_VI / HLSS30_VI v2.0) for the
   same granule, compared over the lesson's clear pixels.

Usage:

    python scripts/check_hls_ndvi.py \
        outputs/hls-vegetation-map/python/pando_2024-08-27_ndvi_provenance.json \
        --record tutorials/hls-vegetation-map/validation/<date>-local-python-checks.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.windows import from_bounds

LOG = logging.getLogger("check_hls_ndvi")
CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
HLS_SCALE = 0.0001
COOKIES = Path.home() / ".cache" / "trees-from-space" / "earthdata-cookies.txt"
GDAL_OPTIONS = {
    "GDAL_HTTP_NETRC": "YES",
    "GDAL_HTTP_COOKIEFILE": str(COOKIES),
    "GDAL_HTTP_COOKIEJAR": str(COOKIES),
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


@dataclass
class PixelCheck:
    row: int
    col: int
    x_m: float
    y_m: float
    red_stored: int
    nir_stored: int
    red_reflectance: float
    nir_reflectance: float
    ndvi_by_hand: float
    ndvi_lesson: float
    abs_diff: float


def vi_ndvi_url(granule_id: str, product: str) -> str | None:
    """Find the NDVI file of the HLS VI granule matching ``granule_id``."""
    vi_id = "HLS-VI." + granule_id.removeprefix("HLS.")
    params = {
        "short_name": f"{product}_VI",
        "version": "2.0",
        "readable_granule_name": vi_id,
    }
    response = requests.get(CMR, params=params, timeout=60)
    response.raise_for_status()
    for item in response.json()["items"]:
        for link in item["umm"].get("RelatedUrls", []):
            url = link.get("URL", "")
            if url.startswith("https://") and url.endswith(".NDVI.tif"):
                return url
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--points", type=int, default=5, help="random clear pixels")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--record", type=Path, help="write the result as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    provenance = json.loads(args.provenance.read_text())
    selected = provenance["selected_granule"]
    ndvi_path = args.provenance.with_name(
        args.provenance.name.replace("_provenance.json", ".tif")
    )
    with rasterio.open(ndvi_path) as src:
        ndvi = src.read(1)
        transform, crs, bounds = src.transform, src.crs, src.bounds

    rng = np.random.default_rng(42)
    finite_rows, finite_cols = np.nonzero(np.isfinite(ndvi))
    picks = rng.choice(len(finite_rows), size=args.points, replace=False)
    pixels = [(ndvi.shape[0] // 2, ndvi.shape[1] // 2)] + [
        (int(finite_rows[i]), int(finite_cols[i])) for i in picks
    ]

    checks = []
    with rasterio.Env(**GDAL_OPTIONS):
        coords = [transform * (col + 0.5, row + 0.5) for row, col in pixels]
        with rasterio.open(f"/vsicurl/{selected['source_urls']['red']}") as red_src:
            reds = [int(v[0]) for v in red_src.sample(coords)]
        with rasterio.open(f"/vsicurl/{selected['source_urls']['nir']}") as nir_src:
            nirs = [int(v[0]) for v in nir_src.sample(coords)]
        for (row, col), (x, y), red, nir in zip(
            pixels, coords, reds, nirs, strict=True
        ):
            red_r, nir_r = red * HLS_SCALE, nir * HLS_SCALE
            by_hand = (nir_r - red_r) / (nir_r + red_r)
            lesson = float(ndvi[row, col])
            checks.append(
                PixelCheck(
                    row=row,
                    col=col,
                    x_m=x,
                    y_m=y,
                    red_stored=red,
                    nir_stored=nir,
                    red_reflectance=round(red_r, 6),
                    nir_reflectance=round(nir_r, 6),
                    ndvi_by_hand=round(by_hand, 7),
                    ndvi_lesson=round(lesson, 7),
                    abs_diff=abs(by_hand - lesson) if np.isfinite(lesson) else None,
                )
            )

        vi_url = vi_ndvi_url(selected["granule_id"], selected["product"])
        vi_result = {"granule_found": vi_url is not None}
        if vi_url:
            with rasterio.open(f"/vsicurl/{vi_url}") as vi_src:
                window = from_bounds(*bounds, vi_src.transform).round_offsets()
                window = window.round_lengths()
                vi_raw = vi_src.read(1, window=window).astype("float64")
                vi_valid = vi_raw != vi_src.nodata
                vi = vi_raw * vi_src.scales[0] + vi_src.offsets[0]
                same_grid = vi_src.crs == crs and vi_src.window_transform(window) == (
                    transform
                )
            both = np.isfinite(ndvi) & vi_valid
            diff = ndvi[both] - vi[both]
            vi_result.update(
                {
                    "file": Path(vi_url).name,
                    "same_grid": bool(same_grid),
                    "pixels_compared": int(both.sum()),
                    "mean_diff": round(float(diff.mean()), 6),
                    "mean_abs_diff": round(float(np.abs(diff).mean()), 6),
                    "max_abs_diff": round(float(np.abs(diff).max()), 6),
                    "pearson_r": round(
                        float(np.corrcoef(ndvi[both], vi[both])[0, 1]), 6
                    ),
                    "vi_scale": vi_src.scales[0],
                }
            )

    worst = max(c.abs_diff for c in checks if c.abs_diff is not None)
    result = {
        "check": "hls-ndvi-independent",
        "lesson_output": ndvi_path.name,
        "language": provenance.get("language"),
        "granule_id": selected["granule_id"],
        "known_pixels": [asdict(c) for c in checks],
        "known_pixels_max_abs_diff": worst,
        "known_pixels_pass": worst <= args.tolerance,
        "hls_vi_comparison": vi_result,
    }
    text = json.dumps(result, indent=1)
    print(text)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(text + "\n")
        LOG.info("Recorded %s", args.record)
    return 0 if result["known_pixels_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
