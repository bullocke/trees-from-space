"""Check data coverage for candidate study sites before adopting them.

For each site box, the script counts catalog matches for the products the
tutorial sequence plans to use, using metadata only (no data are downloaded
and no login is needed):

- HLS L30 and S30 v2.0 in a summer window for each year, with the number of
  granules whose tile-wide cloud cover is below a threshold, and the MGRS
  tiles that intersect the box (HLS granules are tiled)
- GEDI L2A v002 and L4A v2.1 footprint granules (whole mission)
- NISAR GCOV (beta and provisional releases) and GUNW (provisional)
- MODIS MOD13Q1 v061, Daymet V4R1 daily, and ECOSTRESS LSTE v002 for a year
- Sentinel-2 L2A items through the Earth Search STAC API
- NEON airborne lidar and canopy height years, for NEON sites

Usage:

    python scripts/check_site_coverage.py --year 2024 --out coverage.json
    python scripts/check_site_coverage.py --sites examples/sites.geojson

Without ``--sites`` the script checks the built-in candidate list.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests

LOG = logging.getLogger("check_site_coverage")
CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
EARTH_SEARCH = "https://earth-search.aws.element84.com/v1/search"
NEON_SITES = "https://data.neonscience.org/api/v0/sites/{code}"
TIMEOUT_S = 60

# (label, short_name, version or None, whole_mission)
PRODUCTS = [
    ("GEDI L2A v002", "GEDI02_A", "002", True),
    ("GEDI L4A v2.1", "GEDI_L4A_AGB_Density_V2_1_2056", "2.1", True),
    ("NISAR GCOV beta", "NISAR_L2_GCOV_BETA_V1", None, True),
    ("NISAR GCOV provisional", "NISAR_L2_GCOV_PROVISIONAL_V1", None, True),
    ("NISAR GUNW provisional", "NISAR_L2_GUNW_PROVISIONAL_V1", None, True),
    ("MODIS MOD13Q1 v061", "MOD13Q1", "061", False),
    ("Daymet V4R1 daily", "Daymet_Daily_V4R1_2129", "4.1", False),
    ("ECOSTRESS LSTE v002", "ECO_L2T_LSTE", "002", False),
]
NEON_AOP = {"DP1.30003.001": "lidar point cloud", "DP3.30015.001": "canopy height"}

# Candidate sites: (site_id, name, center lat, center lon, NEON site code)
CANDIDATES = [
    (
        "pando",
        "Pando aspen stand and Fish Lake, Fishlake NF, Utah",
        38.525,
        -111.75,
        None,
    ),
    (
        "wref",
        "Wind River Experimental Forest, Washington (NEON WREF)",
        45.82049,
        -121.95191,
        "WREF",
    ),
    ("teak", "Lower Teakettle, California (NEON TEAK)", 37.00583, -119.00602, "TEAK"),
    ("niwo", "Niwot Ridge, Colorado (NEON NIWO)", 40.05425, -105.58237, "NIWO"),
    ("rmnp", "Rocky Mountains, Colorado (NEON RMNP)", 40.275903, -105.545955, "RMNP"),
]


@dataclass
class SiteCoverage:
    """Catalog coverage for one site box."""

    site_id: str
    name: str
    bbox: tuple[float, float, float, float]
    hls_tiles: list[str] = field(default_factory=list)
    hls_summer: dict[str, dict[str, int]] = field(default_factory=dict)
    products: dict[str, int] = field(default_factory=dict)
    sentinel2_items: int | None = None
    neon_aop_years: dict[str, list[str]] = field(default_factory=dict)


def box_around(lat: float, lon: float, half_km: float = 3.3) -> tuple[float, ...]:
    """Return a (west, south, east, north) box of about 2 * half_km on a side."""
    dlat = half_km / 111.32
    dlon = half_km / (111.32 * math.cos(math.radians(lat)))
    return tuple(round(v, 3) for v in (lon - dlon, lat - dlat, lon + dlon, lat + dlat))


def cmr_hits(short_name: str, version: str | None, bbox, temporal=None) -> int:
    params = {
        "short_name": short_name,
        "bounding_box": ",".join(map(str, bbox)),
        "page_size": 0,
    }
    if version:
        params["version"] = version
    if temporal:
        params["temporal"] = ",".join(temporal)
    response = requests.get(CMR, params=params, timeout=TIMEOUT_S)
    response.raise_for_status()
    return int(response.headers["CMR-Hits"])


def hls_summer(bbox, year: int, cloud_max: float) -> tuple[dict, set[str]]:
    """Count HLS granules in a 15 July to 15 September window."""
    temporal = (f"{year}-07-15T00:00:00Z", f"{year}-09-15T23:59:59Z")
    counts, tiles = {}, set()
    for short_name in ("HLSL30", "HLSS30"):
        params = {
            "short_name": short_name,
            "version": "2.0",
            "bounding_box": ",".join(map(str, bbox)),
            "temporal": ",".join(temporal),
            "page_size": 200,
        }
        response = requests.get(CMR, params=params, timeout=TIMEOUT_S)
        response.raise_for_status()
        items = response.json()["items"]
        low_cloud = 0
        for item in items:
            umm = item["umm"]
            tiles.add(umm["GranuleUR"].split(".")[2])
            attrs = {a["Name"]: a["Values"][0] for a in umm["AdditionalAttributes"]}
            if float(attrs.get("CLOUD_COVERAGE", 100)) < cloud_max:
                low_cloud += 1
        counts[short_name] = {"granules": len(items), "low_cloud": low_cloud}
    return counts, tiles


def sentinel2_count(bbox, year: int) -> int | None:
    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{year}-07-15T00:00:00Z/{year}-09-15T23:59:59Z",
        "limit": 1,
    }
    try:
        response = requests.post(EARTH_SEARCH, json=body, timeout=TIMEOUT_S)
        response.raise_for_status()
        return response.json().get("numberMatched")
    except requests.RequestException as error:
        LOG.warning("Earth Search query failed: %s", error)
        return None


def neon_years(code: str) -> dict[str, list[str]]:
    response = requests.get(NEON_SITES.format(code=code), timeout=TIMEOUT_S)
    response.raise_for_status()
    years = {}
    for product in response.json()["data"]["dataProducts"]:
        if product["dataProductCode"] in NEON_AOP:
            label = NEON_AOP[product["dataProductCode"]]
            years[label] = sorted({m[:4] for m in product["availableMonths"]})
    return years


def check(site, year: int, years: list[int], cloud_max: float) -> SiteCoverage:
    site_id, name, bbox, neon_code = site
    result = SiteCoverage(site_id=site_id, name=name, bbox=bbox)
    all_tiles: Counter[str] = Counter()
    for y in years:
        counts, tiles = hls_summer(bbox, y, cloud_max)
        result.hls_summer[str(y)] = {k: v for k, v in counts.items()}
        all_tiles.update(tiles)
    result.hls_tiles = sorted(all_tiles)
    window = (f"{year}-01-01T00:00:00Z", f"{year}-12-31T23:59:59Z")
    for label, short_name, version, whole_mission in PRODUCTS:
        temporal = None if whole_mission else window
        result.products[label] = cmr_hits(short_name, version, bbox, temporal)
    result.sentinel2_items = sentinel2_count(bbox, year)
    if neon_code:
        result.neon_aop_years = neon_years(neon_code)
    return result


def load_sites(path: Path | None) -> list[tuple]:
    if path is None:
        return [
            (sid, name, box_around(lat, lon), code)
            for sid, name, lat, lon, code in CANDIDATES
        ]
    sites = []
    for feature in json.loads(path.read_text())["features"]:
        ring = feature["geometry"]["coordinates"][0]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        props = feature["properties"]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        sites.append((props["site_id"], props["name"], bbox, props.get("neon_site")))
    return sites


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sites", type=Path, help="GeoJSON of site boxes")
    parser.add_argument("--year", type=int, default=2024, help="year for counts")
    parser.add_argument(
        "--hls-years",
        type=int,
        nargs="+",
        default=[2021, 2022, 2023, 2024, 2025],
        help="years for the HLS summer-window counts",
    )
    parser.add_argument("--cloud-max", type=float, default=20.0)
    parser.add_argument("--out", type=Path, help="write results as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    results = []
    for site in load_sites(args.sites):
        LOG.info("Checking %s %s", site[0], site[2])
        results.append(check(site, args.year, args.hls_years, args.cloud_max))
    report = [asdict(r) for r in results]
    text = json.dumps(report, indent=1)
    if args.out:
        args.out.write_text(text + "\n")
        LOG.info("Wrote %s", args.out)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
