"""Check the GEDI lesson's Harmony subsets against the original granules.

For a few granules, the script opens the original (about 2 GB) GEDI L2A file
remotely through earthaccess, reads one beam's shot numbers, finds the
footprints that Harmony returned for that beam, and compares their position,
RH98, and quality fields value by value. It reads only the arrays it needs,
not the whole granule. An Earthdata Login in ~/.netrc is required.

Usage:

    python scripts/check_gedi_subset.py \
        outputs/gedi-canopy-height/python/pando_gedi_l2a_v003_provenance.json \
        --record tutorials/gedi-canopy-height/validation/<date>-local-python-checks.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import earthaccess
import h5py
import numpy as np

LOG = logging.getLogger("check_gedi_subset")
FIELDS = ["lat_lowestmode", "lon_lowestmode", "l2a_quality_flag_rel3", "degrade_flag"]


def subset_beams(path: Path) -> dict[str, dict[str, np.ndarray]]:
    """Read the subset file's beams that hold footprints."""
    beams = {}
    with h5py.File(path, "r") as subset:
        for beam in subset:
            group = subset[beam]
            if not beam.startswith("BEAM") or "shot_number" not in group:
                continue
            if group["shot_number"].shape[0] == 0:
                continue
            beams[beam] = {
                "shot_number": group["shot_number"][:],
                "rh98": group["rh"][:, 98],
                **{field: group[field][:] for field in FIELDS},
            }
    return beams


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--granules", type=int, default=2, help="granules to check")
    parser.add_argument("--cache-dir", type=Path, help="lesson cache (default: repo)")
    parser.add_argument("--record", type=Path, help="write the result as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    provenance = json.loads(args.provenance.read_text())
    repo = Path(__file__).resolve().parents[1]
    cache = args.cache_dir or repo / "cache"
    bbox = provenance["settings"]["bbox_wsen_deg"]
    box_name = "_".join(f"{value:.4f}" for value in bbox)
    site_cache = cache / "gedi" / f"{provenance['settings']['site_id']}_{box_name}"
    subset_dir = next(p for p in site_cache.glob("harmony_*") if p.is_dir())
    files = sorted(
        subset_dir.glob("*.h5"), key=lambda p: p.stat().st_size, reverse=True
    )

    earthaccess.login(strategy="netrc")
    checks = []
    for path in files[: args.granules]:
        granule_id = path.name[path.name.index("GEDI02_A") :].split("_subsetted")[0]
        beams = subset_beams(path)
        beam = max(beams, key=lambda b: beams[b]["shot_number"].size)
        mine = beams[beam]
        results = earthaccess.search_data(
            short_name="GEDI02_A", version="003", granule_name=f"{granule_id}*"
        )
        remote = earthaccess.open(results[:1])[0]  # a file object read over HTTPS
        with h5py.File(remote, "r") as full:
            group = full[beam]
            shots = group["shot_number"][:]
            index = np.flatnonzero(np.isin(shots, mine["shot_number"]))
            original = {
                "shot_number": shots[index],
                "rh98": group["rh"][index.min() : index.max() + 1, 98][
                    index - index.min()
                ],
                **{
                    field: group[field][index.min() : index.max() + 1][
                        index - index.min()
                    ]
                    for field in FIELDS
                },
            }
        remote.close()
        order = np.argsort(mine["shot_number"])
        mine = {k: v[order] for k, v in mine.items()}
        order = np.argsort(original["shot_number"])
        original = {k: v[order] for k, v in original.items()}
        identical = {
            k: bool(np.array_equal(mine[k], original[k], equal_nan=True))
            for k in ["shot_number", "rh98", *FIELDS]
        }
        checks.append(
            {
                "granule_id": granule_id,
                "beam": beam,
                "footprints_in_subset": int(mine["shot_number"].size),
                "footprints_found_in_original": int(index.size),
                "identical": identical,
            }
        )
        LOG.info("%s %s: %s", granule_id, beam, identical)

    result = {
        "check": "gedi-harmony-subset-vs-original",
        "checks": checks,
        "passed": all(
            c["footprints_in_subset"] == c["footprints_found_in_original"]
            and all(c["identical"].values())
            for c in checks
        ),
    }
    text = json.dumps(result, indent=1)
    print(text)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(text + "\n")
        LOG.info("Recorded %s", args.record)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
