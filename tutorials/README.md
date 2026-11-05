# Tutorial index

Each lesson answers one question with one data access route and produces one result. Start with **Getting started**, which checks your setup. Lessons are listed in the suggested order.

**Status** means: *planned* (not written yet), *implemented* (written and run by its author), or *tested* (passed the [validation checklist](../docs/contributing.md#validation-checklist) on at least one platform). The validation table below shows exactly where each lesson has run.

## Lessons

| # | Lesson | You will | Languages | Level | Data and time | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Getting started](getting-started/) | Check your environment, storage, network access, and Earthdata credentials, and save a report | Python, R | Beginner | No downloads, about 5 min | Tested (local, CHPC; Python in Colab) |
| 2 | [HLS vegetation map](hls-vegetation-map/) | Map vegetation greenness (NDVI) around a forest site with Harmonized Landsat Sentinel-2 data from NASA Earthdata | Python, R | Beginner | About 0.4 MB, 15 to 30 min | Tested (local, CHPC; Python in Colab) |
| 3 | [Sentinel-2 through STAC](sentinel2-stac/) | Find public Sentinel-2 imagery in a STAC catalog and map Pando in true color and NDVI at 10 m | Python, R | Beginner | About 3 MB, 15 to 30 min, no account | Tested (local, CHPC, Colab; R local, CHPC) |
| 4 | [GEDI canopy height](gedi-canopy-height/) | Subset GEDI lidar footprints with NASA Harmony, screen them with the quality flags, and map canopy height (RH98) around Pando | Python, R | Intermediate | About 5 MB, 25 min plus Harmony processing | Tested (local, CHPC, Colab; R local) |
| 5 | [NISAR radar backscatter and change](nisar-backscatter/) | Read NISAR radar images over the internet without downloading them, map L-band backscatter, and find and date forest harvests with a year of backscatter and 12-day coherence | Python | Intermediate | About 40 MB cached (0.7 GB read remotely), 60 min plus 8 min of reading | Tested (local, CHPC, Colab) |
| 6 | Site time series | Extract vegetation and climate observations (MODIS, Daymet) for a site | Python | Intermediate | | Planned |
| 7 | ECOSTRESS | Explore land surface temperature at a site | Python | Intermediate | | Planned |

Later modules will cover NEON airborne lidar and imaging spectroscopy, NAIP, SMAP soil moisture, fire observations, EMIT, longer Landsat records, Google Earth Engine, and carbon-cycle products. Lessons 3 to 7 list Python first; R versions follow where practical.

## Validation

Each cell gives the date of the most recent successful run, or *untested*. Details, including runtime, memory, and data volume, are in each lesson's README.

| Lesson | Language | Local (Linux/WSL) | CHPC OnDemand, compute node | CHPC transfer job | Colab |
| --- | --- | --- | --- | --- | --- |
| Getting started | Python | 2026-11-03 | 2026-11-04 | untested | 2026-11-04 |
| Getting started | R | 2026-11-03 | 2026-11-04 | untested | not supported yet |
| HLS vegetation map | Python | 2026-11-03 | 2026-11-04 | 2026-11-04 | 2026-11-04 |
| HLS vegetation map | R | 2026-11-03 | 2026-11-04 | 2026-11-04 | not supported yet |
| Sentinel-2 through STAC | Python | 2026-11-04 | 2026-11-04 | untested | 2026-11-04 |
| Sentinel-2 through STAC | R | 2026-11-04 | 2026-11-04 | untested | not supported yet |
| GEDI canopy height | Python | 2026-11-04 | 2026-11-04 | untested | 2026-11-04 |
| GEDI canopy height | R | 2026-11-04 | untested | untested | not supported yet |
| NISAR backscatter and change | Python | 2026-11-04 | 2026-11-05 | untested | 2026-11-05 |

Local runs used WSL (Ubuntu 22.04) with the environments in [`environments/`](../environments/). Each lesson was run from an empty cache, again from the cache, and offline (`TFS_OFFLINE=1`, which simulates a CHPC compute node).

CHPC runs used OnDemand Jupyter on the `notchpeak-shared-short` partition, which could download data in our tests, and transfer jobs on `notchpeak-dtn`.

**Validation still to do.** The GEDI R lesson in CHPC OnDemand; the Sentinel-2, GEDI, and NISAR lessons as transfer jobs (optional); the getting-started notebooks as transfer jobs (optional, since they download nothing); R in Colab (not supported until tested); and an RStudio route for the R lessons.
