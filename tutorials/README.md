# Tutorial index

Each lesson answers one question with one data access route and produces one result. Start with **Getting started**, which checks your setup. Lessons are listed in the suggested order.

**Status** means: *planned* (not written yet), *implemented* (written and run by its author), or *tested* (passed the [validation checklist](../docs/contributing.md#validation-checklist) on at least one platform). The validation table below shows exactly where each lesson has run.

## Lessons

| # | Lesson | You will | Languages | Level | Data and time | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Getting started](getting-started/) | Check your environment, storage, network access, and Earthdata credentials, and save a report | Python, R | Beginner | No downloads, about 5 min | Tested (local; Python in Colab) |
| 2 | [HLS vegetation map](hls-vegetation-map/) | Map vegetation greenness (NDVI) around a forest site with Harmonized Landsat Sentinel-2 data from NASA Earthdata | Python, R | Beginner | About 0.4 MB, 15 to 30 min | Tested (local; Python on a CHPC transfer job and in Colab) |
| 3 | Sentinel-2 through STAC | Find and read imagery from a STAC catalog | Python | Beginner | | Planned |
| 4 | GEDI canopy structure | Map quality-screened canopy-height footprints | Python | Intermediate | | Planned |
| 5 | NISAR GCOV | Read and visualize radar backscatter for one polarization | Python | Intermediate | | Planned |
| 6 | Site time series | Extract vegetation and climate observations (MODIS, Daymet) for a site | Python | Intermediate | | Planned |
| 7 | ECOSTRESS | Explore land surface temperature at a site | Python | Intermediate | | Planned |

Later modules will cover NEON airborne lidar and imaging spectroscopy, NAIP, SMAP soil moisture, fire observations, EMIT, longer Landsat records, Google Earth Engine, and carbon-cycle products. Lessons 3 to 7 list Python first; R versions follow where practical.

## Validation

Each cell gives the date of the most recent successful run, or *untested*. Details, including runtime, memory, and data volume, are in each lesson's README.

| Lesson | Language | Local (Linux/WSL) | CHPC OnDemand, compute node | CHPC OnDemand, Frisco | CHPC transfer job | Colab |
| --- | --- | --- | --- | --- | --- | --- |
| Getting started | Python | 2026-11-03 | failed to launch (fix pending retest) | untested | untested | 2026-11-04 |
| Getting started | R | 2026-11-03 | untested | untested | untested | not supported yet |
| HLS vegetation map | Python | 2026-11-03 | untested | untested | 2026-11-04 | 2026-11-04 |
| HLS vegetation map | R | 2026-11-03 | untested | untested | untested | not supported yet |

Local runs used WSL (Ubuntu 22.04) with the environments in [`environments/`](../environments/). Each lesson was run from an empty cache, again from the cache, and offline (`TFS_OFFLINE=1`, which simulates a CHPC compute node).

**Validation still to do.** CHPC OnDemand: the first launch failed because the environment was not on `PATH`; the [CHPC guide](../docs/getting-started/chpc.md) now uses a different setup, which needs a retest. After that: the getting-started notebooks on a compute node and a Frisco node, the HLS lesson offline in OnDemand after the transfer job, the R notebooks on CHPC, and the getting-started notebook as a transfer job. R in Colab is not supported until tested.
