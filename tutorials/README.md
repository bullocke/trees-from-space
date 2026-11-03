# Tutorial index

Each lesson answers one question with one data access route and produces one result. Start with **Getting started**, which checks your setup. Lessons are listed in the suggested order.

**Status** means: *planned* (not written yet), *implemented* (written and run by its author), or *tested* (passed the [validation checklist](../docs/contributing.md#validation-checklist) on at least one platform). The validation table below shows exactly where each lesson has run.

## Lessons

| # | Lesson | You will | Languages | Level | Data and time | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Getting started](getting-started/) | Check your environment, storage, network access, and Earthdata credentials, and save a report | Python, R | Beginner | No downloads, about 5 min | Python tested, R planned |
| 2 | HLS vegetation map | Map vegetation greenness (NDVI) around a forest site with Harmonized Landsat Sentinel-2 data from NASA Earthdata | Python, R | Beginner | A few MB, 15 to 30 min | Planned |
| 3 | Sentinel-2 through STAC | Find and read imagery from a STAC catalog | Python | Beginner | Planned | Planned |
| 4 | GEDI canopy structure | Map quality-screened canopy-height footprints | Python | Intermediate | Planned | Planned |
| 5 | NISAR GCOV | Read and visualize radar backscatter for one polarization | Python | Intermediate | Planned | Planned |
| 6 | Site time series | Extract vegetation and climate observations (MODIS, Daymet) for a site | Python | Intermediate | Planned | Planned |
| 7 | ECOSTRESS | Explore land surface temperature at a site | Python | Intermediate | Planned | Planned |

Later modules will cover NEON airborne lidar and imaging spectroscopy, NAIP, SMAP soil moisture, fire observations, EMIT, longer Landsat records, Google Earth Engine, and carbon-cycle products.

## Validation

Each cell gives the date of the most recent successful run, or *untested*. Details, including runtime, memory, and data volume, are in each lesson's README.

| Lesson | Language | Local (Linux/WSL) | CHPC OnDemand, compute node | CHPC OnDemand, Frisco | CHPC transfer job | Colab |
| --- | --- | --- | --- | --- | --- | --- |
| Getting started | Python | 2026-11-03 | untested | untested | untested | untested |
| Getting started | R | untested | untested | untested | untested | untested |
