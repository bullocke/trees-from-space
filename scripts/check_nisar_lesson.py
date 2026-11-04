"""Check the NISAR lesson's results against the source files and Sentinel-2.

The script runs four independent checks on a finished run of the lesson:

1. Known pixels. It samples valid pixels of the lesson's 10 m backscatter map,
   finds each pixel's position in the original GCOV file from its own
   coordinate arrays (not the lesson's window logic), reads that one value
   remotely, and compares the two in dB.
2. Aggregation. For a few dates it re-reads 10 m HH and HV around sampled 20 m
   blocks and recomputes the 2 x 2 means of valid pixels stored in the cache.
3. Coherence. For a few pairs it reads the GUNW 80 m coherence layer and
   compares it with the lesson's 20 m coherence averaged to 80 m (rank
   correlation).
4. Sentinel-2. It computes the NDVI change between two Sentinel-2 L2A images
   (Earth Search, Collection 1) a year apart on the site's tile, on the
   lesson's 20 m grid, and reports it for harvest patches, for patches that
   backscatter flagged but coherence set aside, and for unchanged pixels.

An Earthdata Login in ~/.netrc is required for checks 1 to 3. Usage:

    python scripts/check_nisar_lesson.py \
        outputs/nisar-backscatter/python/cowlitz_nisar_provenance.json \
        --record tutorials/nisar-backscatter/validation/<date>-local-python-checks.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import earthaccess
import h5py
import numpy as np
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject
from rasterio.warp import transform as transform_points

LOG = logging.getLogger("check_nisar_lesson")
NISAR_HTTPS = "https://nisar.asf.earthdatacloud.nasa.gov/NISAR"
GCOV_GRID = "science/LSAR/GCOV/grids/frequencyA"
GUNW_GRID = "science/LSAR/GUNW/grids/frequencyA"
EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"


@dataclass
class CheckResult:
    """Outcome of the four checks."""

    check: str = "nisar-backscatter lesson against source files and Sentinel-2"
    provenance: str = ""
    known_pixels: dict = field(default_factory=dict)
    aggregation: dict = field(default_factory=dict)
    coherence_80m: dict = field(default_factory=dict)
    sentinel2: dict = field(default_factory=dict)
    passed: bool = False


def granule_url(short_name: str, granule_id: str) -> str:
    return f"{NISAR_HTTPS}/{short_name}/{granule_id}/{granule_id}.h5"


def open_remote(fs, url: str):
    return fs.open(url, block_size=2**20, cache_type="blockcache")


def nearest_index(coordinates: np.ndarray, value: float) -> int:
    return int(np.abs(coordinates - value).argmin())


def check_known_pixels(fs, provenance: dict, output_dir: Path, n: int, rng) -> dict:
    """Compare sampled map pixels with single values read from the source file."""
    settings = provenance["settings"]
    path = (
        output_dir / f"{settings['site_id']}_{settings['map_date']}_gcov_gamma0_db.tif"
    )
    with rasterio.open(path) as src:
        hv_db = src.read(2).astype("float64")
        crs, transform = src.crs, src.transform
    rows, cols = np.nonzero(np.isfinite(hv_db))
    pick = rng.choice(rows.size, size=n, replace=False)
    xs, ys = rasterio.transform.xy(transform, rows[pick], cols[pick])
    lons, lats = transform_points(crs, "EPSG:4326", xs, ys)
    url = granule_url(
        provenance["products"]["gcov"]["short_name"], provenance["map_granule"]
    )
    differences = []
    with open_remote(fs, url) as remote, h5py.File(remote, "r") as h5:
        group = h5[GCOV_GRID]
        x, y = group["xCoordinates"][:], group["yCoordinates"][:]
        epsg = int(group["projection"][()])
        px, py = transform_points("EPSG:4326", f"EPSG:{epsg}", lons, lats)
        for k, (u, v) in enumerate(zip(px, py)):
            source = float(group["HVHV"][nearest_index(y, v), nearest_index(x, u)])
            mine = hv_db[rows[pick][k], cols[pick][k]]
            differences.append(abs(10 * np.log10(source) - mine))
    worst = float(max(differences))
    LOG.info("Known pixels: %d sampled, largest difference %.2e dB", n, worst)
    return {"pixels": n, "max_abs_diff_db": worst, "passed": worst < 1e-3}


def check_aggregation(fs, provenance: dict, cache: Path, n_dates: int, rng) -> dict:
    """Recompute sampled 2 x 2 block means from the source files."""
    grid10, grid20 = provenance["grid_10m"], provenance["grid_20m"]
    short_name = provenance["products"]["gcov"]["short_name"]
    granules = rng.choice(provenance["gcov_granules"], size=n_dates, replace=False)
    worst, blocks = 0.0, 0
    for granule_id in granules:
        with rasterio.open(cache / f"gcov20m_{granule_id}.tif") as src:
            cached = {
                d: src.read(i).astype("float64")
                for i, d in enumerate(src.descriptions, 1)
            }
        with open_remote(fs, granule_url(short_name, granule_id)) as remote, h5py.File(
            remote, "r"
        ) as h5:
            group = h5[GCOV_GRID]
            x = group["xCoordinates"][:]
            y = group["yCoordinates"][:]
            col0 = nearest_index(x, grid10["x_left"] + grid10["dx"] / 2)
            row0 = nearest_index(y, grid10["y_top"] - grid10["dx"] / 2)
            for r, c in zip(
                rng.integers(0, grid20["height"], 20),
                rng.integers(0, grid20["width"], 20),
            ):
                rows = slice(row0 + 2 * r, row0 + 2 * r + 2)
                cols = slice(col0 + 2 * c, col0 + 2 * c + 2)
                mask = group["mask"][rows, cols]
                for name, band in (("HHHH", "HH"), ("HVHV", "HV")):
                    values = group[name][rows, cols].astype("float64")
                    ok = (mask >= 1) & (mask <= 254) & (values > 0)
                    expected = values[ok].mean() if ok.any() else np.nan
                    stored = cached[band][r, c]
                    if np.isnan(expected) and np.isnan(stored):
                        continue
                    worst = max(worst, abs(stored - expected) / expected)
                blocks += 1
    LOG.info("Aggregation: %d blocks, largest relative difference %.2e", blocks, worst)
    return {
        "dates": len(granules),
        "blocks": blocks,
        "max_rel_diff": worst,
        "passed": worst < 1e-6,
    }


def rank_correlation(a: np.ndarray, b: np.ndarray) -> float:
    ranks_a = np.argsort(np.argsort(a))
    ranks_b = np.argsort(np.argsort(b))
    return float(np.corrcoef(ranks_a, ranks_b)[0, 1])


def check_coherence(fs, provenance: dict, cache: Path, n_pairs: int, rng) -> dict:
    """Compare the lesson's 20 m coherence, averaged to 80 m, with the 80 m layer."""
    grid20 = provenance["grid_20m"]
    short_name = provenance["products"]["gunw"]["short_name"]
    pairs = rng.choice(provenance["gunw_granules"], size=n_pairs, replace=False)
    results = []
    for granule_id in pairs:
        with rasterio.open(cache / f"gunw20m_{granule_id}.tif") as src:
            coherence20 = src.read(1).astype("float64")
        with open_remote(fs, granule_url(short_name, granule_id)) as remote, h5py.File(
            remote, "r"
        ) as h5:
            group = h5[f"{GUNW_GRID}/unwrappedInterferogram"]
            x, y = group["xCoordinates"][:], group["yCoordinates"][:]
            dx = float(x[1] - x[0])
            cols = np.nonzero(
                (x > grid20["x_left"])
                & (x < grid20["x_left"] + grid20["width"] * grid20["dx"])
            )[0]
            rows = np.nonzero(
                (y < grid20["y_top"])
                & (y > grid20["y_top"] - grid20["height"] * grid20["dx"])
            )[0]
            coherence80 = group["HH/coherenceMagnitude"][
                rows.min() : rows.max() + 1, cols.min() : cols.max() + 1
            ]
        sums = np.zeros(coherence80.shape)
        counts = np.zeros(coherence80.shape)
        r20, c20 = np.nonzero(np.isfinite(coherence20))
        x20 = grid20["x_left"] + (c20 + 0.5) * grid20["dx"]
        y20 = grid20["y_top"] - (r20 + 0.5) * grid20["dx"]
        i80 = np.floor((y[rows.min()] + dx / 2 - y20) / dx).astype(int)
        j80 = np.floor((x20 - (x[cols.min()] - dx / 2)) / dx).astype(int)
        inside = (i80 >= 0) & (i80 < sums.shape[0]) & (j80 >= 0) & (j80 < sums.shape[1])
        np.add.at(
            sums, (i80[inside], j80[inside]), coherence20[r20[inside], c20[inside]]
        )
        np.add.at(counts, (i80[inside], j80[inside]), 1)
        mean20 = np.where(counts == 16, sums / np.maximum(counts, 1), np.nan)
        both = np.isfinite(mean20) & np.isfinite(coherence80) & (coherence80 > 0)
        results.append(
            {
                "pair": granule_id,
                "pixels_80m": int(both.sum()),
                "rank_correlation": round(
                    rank_correlation(mean20[both], coherence80[both]), 3
                ),
                "median_20m_mean": round(float(np.median(mean20[both])), 3),
                "median_80m": round(float(np.median(coherence80[both])), 3),
            }
        )
        LOG.info("Coherence %s: %s", granule_id[17:60], results[-1])
    lowest = min(r["rank_correlation"] for r in results)
    return {"pairs": results, "min_rank_correlation": lowest, "passed": lowest > 0.8}


def sentinel2_ndvi(item, grid20: dict) -> np.ndarray:
    """NDVI from one Sentinel-2 L2A item, averaged onto the lesson's 20 m grid."""
    destination = from_origin(
        grid20["x_left"], grid20["y_top"], grid20["dx"], grid20["dx"]
    )
    bands = {}
    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES"):
        for name in ("red", "nir"):
            with rasterio.open(item.assets[name].href) as src:
                scale = src.scales[0]
                offset = src.offsets[0]
                values = np.full((grid20["height"], grid20["width"]), np.nan)
                reproject(
                    rasterio.band(src, 1),
                    values,
                    dst_transform=destination,
                    dst_crs=f"EPSG:{grid20['epsg']}",
                    resampling=Resampling.average,
                    src_nodata=0,
                    dst_nodata=np.nan,
                )
                bands[name] = values * scale + offset
    return (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"])


def find_item(client, tile: str, day: str):
    items = list(
        client.search(
            collections=["sentinel-2-c1-l2a"],
            datetime=f"{day}T00:00:00Z/{day}T23:59:59Z",
            query={"grid:code": {"eq": f"MGRS-{tile.removeprefix('T')}"}},
        ).items()
    )
    if not items:
        raise RuntimeError(f"No Sentinel-2 item for tile {tile} on {day}")
    return min(items, key=lambda item: item.properties["eo:cloud_cover"])


def check_sentinel2(
    provenance: dict, output_dir: Path, sites: Path, before: str, after: str
) -> dict:
    """Compare NDVI change with the lesson's harvest and flagged patches."""
    settings = provenance["settings"]
    tile = next(
        f["properties"]["hls_tile"]
        for f in json.loads(sites.read_text())["features"]
        if f["properties"]["site_id"] == settings["site_id"]
    )
    client = pystac_client.Client.open(EARTH_SEARCH)
    items = [find_item(client, tile, day) for day in (before, after)]
    grid20 = provenance["grid_20m"]
    change = sentinel2_ndvi(items[1], grid20) - sentinel2_ndvi(items[0], grid20)
    ndvi_before = sentinel2_ndvi(items[0], grid20)
    with rasterio.open(output_dir / f"{settings['site_id']}_nisar_change.tif") as src:
        layers = {
            d: src.read(i).astype("float64") for i, d in enumerate(src.descriptions, 1)
        }
    hv_change = layers["HV change, last minus first three dates (dB)"]
    flagged = layers["Flagged by backscatter alone (1 = yes)"] > 0
    patch = layers["Harvest patch number (0 = none)"]
    harvest = patch > 0
    set_aside = flagged & ~harvest
    unchanged = (np.abs(hv_change) < 0.5) & ~flagged
    per_patch = [
        float(np.nanmedian(change[patch == p])) for p in np.unique(patch[harvest])
    ]
    s2_cut = (change < -0.3) & (ndvi_before > 0.8)
    result = {
        "items": [item.id for item in items],
        "ndvi_change_median": {
            "harvest_patches": round(float(np.nanmedian(change[harvest])), 3),
            "set_aside_by_coherence": (
                round(float(np.nanmedian(change[set_aside])), 3)
                if set_aside.any()
                else None
            ),
            "unchanged": round(float(np.nanmedian(change[unchanged])), 3),
        },
        "harvest_patches": len(per_patch),
        "harvest_patches_with_ndvi_loss_over_0.2": int(
            sum(v < -0.2 for v in per_patch)
        ),
        "sentinel2_cut_pixels": int(s2_cut.sum()),
        "sentinel2_cut_pixels_in_harvest_patches": round(
            float((s2_cut & harvest).sum() / max(s2_cut.sum(), 1)), 3
        ),
        "harvest_pixels_with_ndvi_loss_over_0.3": round(
            float(((change < -0.3) & harvest).sum() / max(harvest.sum(), 1)), 3
        ),
    }
    result["passed"] = (
        result["ndvi_change_median"]["harvest_patches"] < -0.2
        and result["harvest_patches_with_ndvi_loss_over_0.2"] >= 0.8 * len(per_patch)
        and abs(result["ndvi_change_median"]["unchanged"]) < 0.05
    )
    LOG.info("Sentinel-2: %s", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("provenance", type=Path)
    parser.add_argument(
        "--cache-dir", type=Path, help="lesson cache root (default: repo cache)"
    )
    parser.add_argument("--pixels", type=int, default=50, help="known pixels to check")
    parser.add_argument(
        "--dates", type=int, default=3, help="dates for the aggregation check"
    )
    parser.add_argument(
        "--pairs", type=int, default=3, help="pairs for the coherence check"
    )
    parser.add_argument(
        "--s2-before", default="2025-09-16", help="Sentinel-2 date before"
    )
    parser.add_argument(
        "--s2-after", default="2026-09-16", help="Sentinel-2 date after"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--record", type=Path, help="write the result as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo = Path(__file__).resolve().parents[1]
    provenance = json.loads(args.provenance.read_text())
    settings = provenance["settings"]
    box_name = "_".join(f"{value:.4f}" for value in settings["bbox_wsen_deg"])
    cache = (
        (args.cache_dir or repo / "cache")
        / "nisar"
        / f"{settings['site_id']}_{box_name}"
    )
    output_dir = args.provenance.parent
    rng = np.random.default_rng(args.seed)

    earthaccess.login(strategy="netrc")
    fs = earthaccess.get_fsspec_https_session()
    result = CheckResult(provenance=args.provenance.name)
    result.known_pixels = check_known_pixels(
        fs, provenance, output_dir, args.pixels, rng
    )
    result.aggregation = check_aggregation(fs, provenance, cache, args.dates, rng)
    result.coherence_80m = check_coherence(fs, provenance, cache, args.pairs, rng)
    result.sentinel2 = check_sentinel2(
        provenance,
        output_dir,
        repo / "examples" / "sites.geojson",
        args.s2_before,
        args.s2_after,
    )
    result.passed = all(
        part["passed"]
        for part in (
            result.known_pixels,
            result.aggregation,
            result.coherence_80m,
            result.sentinel2,
        )
    )
    text = json.dumps(asdict(result), indent=1)
    print(text)
    if args.record:
        args.record.write_text(text + "\n")
        LOG.info("Wrote %s", args.record)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
