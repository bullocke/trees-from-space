"""Check the Sentinel-2 lesson's NDVI against independent calculations.

1. Known pixels. For the window center and a few random clear pixels, read the
   raw stored values from the full remote red (B04) and near-infrared (B08)
   files at the pixel's map coordinates, convert them with ESA's documented
   scale and offset (0.0001 and -0.1), and compute NDVI by hand.
2. NASA's HLS vegetation index (HLSS30_VI v2.0) for the same Sentinel-2
   acquisition. The lesson's 10 m NDVI is averaged onto the HLS 30 m grid and
   compared over pixels valid in both. HLS uses a different atmospheric
   correction, BRDF adjustment, and the narrow near-infrared band (B8A), so
   close agreement, not identity, is expected. Reading HLS needs an Earthdata
   Login in ~/.netrc.

Usage:

    python scripts/check_s2_ndvi.py \
        outputs/sentinel2-stac/python/pando_2024-08-24_s2_provenance.json \
        --record tutorials/sentinel2-stac/validation/<date>-local-python-checks.json
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
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

LOG = logging.getLogger("check_s2_ndvi")
CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
S2_SCALE, S2_OFFSET = 0.0001, -0.1  # ESA, processing baseline 04.00 and later
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
    red_stored: int
    nir_stored: int
    red_reflectance: float
    nir_reflectance: float
    ndvi_by_hand: float
    ndvi_lesson: float
    abs_diff: float


def hls_vi_ndvi_url(item: dict, bbox: list[float]) -> str | None:
    """Find the HLSS30_VI NDVI file for the item's date and tile."""
    day = item["properties"]["datetime"][:10]
    tile = "T" + item["properties"]["grid:code"].split("-")[-1]
    params = {
        "short_name": "HLSS30_VI",
        "version": "2.0",
        "bounding_box": ",".join(map(str, bbox)),
        "temporal": f"{day}T00:00:00Z,{day}T23:59:59Z",
        "page_size": 20,
    }
    response = requests.get(CMR, params=params, timeout=60)
    response.raise_for_status()
    for granule in response.json()["items"]:
        if f".{tile}." not in granule["umm"]["GranuleUR"]:
            continue
        for link in granule["umm"].get("RelatedUrls", []):
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
    item = provenance["source_item"]
    ndvi_path = args.provenance.with_name(
        args.provenance.name.replace("_provenance.json", "_ndvi.tif")
    )
    with rasterio.open(ndvi_path) as src:
        ndvi = src.read(1).astype("float64")
        transform, crs, bounds = src.transform, src.crs, src.bounds

    rng = np.random.default_rng(42)
    rows, cols = np.nonzero(np.isfinite(ndvi))
    picks = rng.choice(len(rows), size=args.points, replace=False)
    pixels = [(ndvi.shape[0] // 2, ndvi.shape[1] // 2)] + [
        (int(rows[i]), int(cols[i])) for i in picks
    ]
    coords = [transform * (col + 0.5, row + 0.5) for row, col in pixels]

    checks = []
    with rasterio.Env(**GDAL_OPTIONS):
        with rasterio.open(item["assets"]["red"]["href"]) as red_src:
            reds = [int(v[0]) for v in red_src.sample(coords)]
        with rasterio.open(item["assets"]["nir"]["href"]) as nir_src:
            nirs = [int(v[0]) for v in nir_src.sample(coords)]
        for (row, col), red, nir in zip(pixels, reds, nirs, strict=True):
            red_r = red * S2_SCALE + S2_OFFSET
            nir_r = nir * S2_SCALE + S2_OFFSET
            by_hand = (nir_r - red_r) / (nir_r + red_r)
            lesson = float(ndvi[row, col])
            checks.append(
                PixelCheck(
                    row=row,
                    col=col,
                    red_stored=red,
                    nir_stored=nir,
                    red_reflectance=round(red_r, 6),
                    nir_reflectance=round(nir_r, 6),
                    ndvi_by_hand=round(by_hand, 7),
                    ndvi_lesson=round(lesson, 7),
                    abs_diff=abs(by_hand - lesson) if np.isfinite(lesson) else None,
                )
            )

        hls_url = hls_vi_ndvi_url(item, provenance["settings"]["bbox_wsen_deg"])
        hls_result: dict = {"granule_found": hls_url is not None}
        if hls_url:
            with rasterio.open(f"/vsicurl/{hls_url}") as hls_src:
                window = from_bounds(*bounds, hls_src.transform)
                window = window.round_offsets(op="ceil").round_lengths(op="floor")
                hls_raw = hls_src.read(1, window=window).astype("float64")
                hls_valid = hls_raw != hls_src.nodata
                hls = hls_raw * hls_src.scales[0] + hls_src.offsets[0]
                hls_transform = hls_src.window_transform(window)
                same_crs = hls_src.crs == crs
            s2_on_hls = np.full(hls.shape, np.nan)
            reproject(
                ndvi,
                s2_on_hls,
                src_transform=transform,
                src_crs=crs,
                src_nodata=np.nan,
                dst_transform=hls_transform,
                dst_crs=crs,
                dst_nodata=np.nan,
                resampling=Resampling.average,
            )
            both = np.isfinite(s2_on_hls) & hls_valid
            diff = s2_on_hls[both] - hls[both]
            hls_result.update(
                {
                    "file": Path(hls_url).name,
                    "same_crs": bool(same_crs),
                    "pixels_compared_30m": int(both.sum()),
                    "mean_diff_s2_minus_hls": round(float(diff.mean()), 4),
                    "mean_abs_diff": round(float(np.abs(diff).mean()), 4),
                    "p95_abs_diff": round(float(np.percentile(np.abs(diff), 95)), 4),
                    "pearson_r": round(
                        float(np.corrcoef(s2_on_hls[both], hls[both])[0, 1]), 4
                    ),
                }
            )

    worst = max(c.abs_diff for c in checks if c.abs_diff is not None)
    result = {
        "check": "s2-ndvi-independent",
        "lesson_output": ndvi_path.name,
        "item_id": item["id"],
        "known_pixels": [asdict(c) for c in checks],
        "known_pixels_max_abs_diff": worst,
        "known_pixels_pass": worst <= args.tolerance,
        "hls_vi_comparison": hls_result,
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
