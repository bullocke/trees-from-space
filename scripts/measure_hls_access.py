"""Compare windowed remote reads with full-file downloads for one HLS granule.

Reads the study-area window of the selected granule's Fmask, red, and
near-infrared files (as the lesson does), then downloads the same three files
in full, and reports elapsed time and bytes received for each approach. Byte
counts come from the host's network counters (/proc/net/dev, Linux only), so
they are approximate and include any other traffic during the measurement.

Usage:

    python scripts/measure_hls_access.py \
        outputs/hls-vegetation-map/python/pando_2024-08-27_ndvi_provenance.json \
        --record tutorials/hls-vegetation-map/validation/2026-11-03-local-access.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import time
from pathlib import Path

import earthaccess
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

LOG = logging.getLogger("measure_hls_access")
COOKIES = Path.home() / ".cache" / "trees-from-space" / "earthdata-cookies.txt"
GDAL_OPTIONS = {
    "GDAL_HTTP_NETRC": "YES",
    "GDAL_HTTP_COOKIEFILE": str(COOKIES),
    "GDAL_HTTP_COOKIEJAR": str(COOKIES),
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "VSI_CACHE": "FALSE",
}


def received_bytes() -> int:
    """Total bytes received on all non-loopback interfaces."""
    total = 0
    for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
        name, data = line.split(":", 1)
        if name.strip() != "lo":
            total += int(data.split()[0])
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    provenance = json.loads(args.provenance.read_text())
    urls = provenance["selected_granule"]["source_urls"]
    bbox = provenance["settings"]["bbox_wsen_deg"]

    before, start = received_bytes(), time.monotonic()
    with rasterio.Env(**GDAL_OPTIONS):
        for url in urls.values():
            with rasterio.open(f"/vsicurl/{url}") as src:
                bounds = transform_bounds("EPSG:4326", src.crs, *bbox, densify_pts=21)
                window = from_bounds(*bounds, src.transform)
                src.read(1, window=window.round_offsets().round_lengths())
    window_s, window_bytes = time.monotonic() - start, received_bytes() - before

    earthaccess.login(strategy="netrc")
    session = earthaccess.get_requests_https_session()
    file_bytes = 0
    before, start = received_bytes(), time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        for url in urls.values():
            target = Path(tmp) / Path(url).name
            with session.get(url, stream=True, timeout=(30, 300)) as response:
                response.raise_for_status()
                with target.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1 << 20):
                        handle.write(chunk)
            file_bytes += target.stat().st_size
    full_s, full_bytes = time.monotonic() - start, received_bytes() - before

    result = {
        "check": "hls-access-comparison",
        "granule_id": provenance["selected_granule"]["granule_id"],
        "files": list(urls),
        "window_read": {
            "seconds": round(window_s, 2),
            "received_mb_approx": round(window_bytes / 1e6, 3),
        },
        "full_download": {
            "seconds": round(full_s, 2),
            "received_mb_approx": round(full_bytes / 1e6, 3),
            "file_mb": round(file_bytes / 1e6, 3),
        },
        "note": "Host network counters; approximate. One granule, three files.",
    }
    text = json.dumps(result, indent=1)
    print(text)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(text + "\n")
        LOG.info("Recorded %s", args.record)
    return 0


if __name__ == "__main__":
    sys.exit(main())
