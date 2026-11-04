# Contributing

This guide covers how lessons are written, organized, and validated. Learners do not need it. They should start with the [README](../README.md) and the [getting-started guides](getting-started/).

## Lesson conventions

Each lesson answers one question with one primary data access route and produces one useful output. Aim for 15 to 30 minutes of learner activity after environment setup, and report download and queue time separately. Split longer material into access, analysis, and optional scaling lessons.

Every lesson follows the same sequence, which the [templates](../templates/) lay out:

1. **Question and outcome.** State the task, show the expected result (a committed PNG), and list two or three learning objectives.
2. **Before starting.** Link the setup guides and list prerequisites, the tested environments, account requirements, expected data volume, and approximate runtime.
3. **Dataset or tool in brief.** Explain the measured or estimated quantity, units, spatial and temporal support, coverage, and one or two limits on interpretation. Method lessons describe assumptions and required inputs instead.
4. **Settings.** Put every learner-editable value in one cell tagged `parameters`: site, dates, product and version, variables, and a small request limit.
5. **Find and inspect.** Search, show a short results table, and check coverage and metadata before retrieving data.
6. **Access and prepare.** Retrieve only what the lesson needs, apply scale factors and quality rules, handle missing values, and align grids where required.
7. **Visualize and analyze.** Produce one main figure or map and a simple summary tied to the opening question.
8. **Save and adapt.** Export the result with provenance, suggest one small exercise, and link further reading.

### Files and names

| Location | Purpose |
| --- | --- |
| `tutorials/<topic>/<topic>-python.ipynb` | Python lesson. The topic is in the file name so that Colab tabs and downloaded copies stay distinguishable. |
| `tutorials/<topic>/<topic>-r.ipynb` | Matching R lesson, where implemented |
| `tutorials/<topic>/README.md` | Product references, requirements, support status, and the validation record |
| `tutorials/<topic>/figures/` | Small committed figures, including the expected result |
| `tutorials/README.md` | Tutorial index |
| `examples/sites.geojson` | Shared study areas with stable `site_id` values |
| `environments/` | Environment specifications and lockfiles |
| `scripts/` | Batch entry points, validation tools, and Slurm templates |

Shared helper code (`helpers/python/`, `helpers/R/`) is added only after two completed lessons need the same function. Until then, lessons keep their logic visible in the notebook.

### Code style

- Use descriptive variable names, small cells, and ordinary functions from established packages.
- Show the search, quality filtering, and analysis steps rather than hiding them in helpers.
- Explain coordinate order, date formats, units, and file paths where they first appear.
- Notebooks use `print` for messages meant for learners. Scripts in `scripts/` use `logging`, type hints, and Black formatting (line length 88).
- Read paths from `TFS_DATA_DIR`, `TFS_CACHE_DIR`, and `TFS_OUTPUT_DIR`, with defaults under the repository root (found through the `.tfs-root` marker file).
- Keep TLS verification on. Never set `GDAL_HTTP_UNSAFESSL`.

### Data handling

- Keep collection identifiers, versions, variables, and dates explicit.
- Distinguish a catalog's search footprint from the pixels or observations actually available inside the study area.
- Teach units, scale factors, offsets, missing values, and quality flags before computing indices or statistics.
- Prefer bounded requests. Show the number of files and the estimated transfer before a substantial download.
- Write every cached file under a temporary name and rename it when complete, so an interrupted run never leaves a partial file that looks valid. A second run must reuse the cache without contacting the provider.
- Save provenance next to outputs: product and version, granule or item IDs, dates, quality rules, processing settings, package versions, and retrieval time. Never save credentials or expiring signed URLs.
- Export rasters as Cloud Optimized GeoTIFF, multidimensional data as NetCDF or Zarr, and small tables as CSV with units in the column names.

## Study sites

Lessons share two study areas, plus a third site for change detection, all defined in [`examples/sites.geojson`](../examples/sites.geojson) with stable `site_id` values. Each is a box about 6.6 km across that lies inside a single HLS/Sentinel-2 MGRS tile. Use another site only when a sensor's coverage or sampling requires it, and add it to the GeoJSON file with the same properties.

| `site_id` | Site | Why |
| --- | --- | --- |
| `pando` | Pando aspen stand and Fish Lake, Fishlake National Forest, Utah (tile T12SVH) | A forest that CHPC users know, with a clear ecological story (aspen decline, browsing, fencing). The lake and meadows give visible contrast on maps. |
| `wref` | Wind River Experimental Forest, Washington (NEON WREF, tile T10TER) | Tall, high-biomass old-growth conifer forest that contrasts with Pando. NEON airborne lidar and canopy height exist for 2017–2019, 2021–2023, and 2025, and NEON field plots support the later structure and biomass lessons. |
| `cowlitz` | Managed forest near Pigeon Springs, Cowlitz County, Washington (tile T10TES) | A change-detection site for the NISAR lesson. Neither shared site lost forest during NISAR's first year, while this box holds several clearcuts made between November 2025 and September 2026, alongside mature and young stands. It lies on the same NISAR track and frame as Wind River, so the lesson can switch between the two. |

`scripts/check_site_coverage.py` produced the selection evidence on 2026-11-03 ([`examples/site-coverage-2026-11-03.json`](../examples/site-coverage-2026-11-03.json)). It counts catalog matches only, so a lesson must still confirm the pixels or footprints available inside the box. For 2024, both sites returned granules for every planned product: HLS (summer window), Sentinel-2 L2A, GEDI L2A and L4A, NISAR GCOV (beta and provisional), MOD13Q1, Daymet, and ECOSTRESS. TEAK spans two MGRS tiles, and the NIWO and RMNP boxes had fewer low-cloud summer HLS scenes, so neither was chosen.

The `cowlitz` site was chosen on 2026-11-04 from NISAR data ([`examples/site-coverage-2026-11-04-cowlitz.json`](../examples/site-coverage-2026-11-04-cowlitz.json) holds its catalog counts). An 80 m screen of NISAR's first year over about 95 by 90 km around Wind River found many forest patches with a step drop in HV backscatter. This box held the most, and the drops matched NDVI losses between Sentinel-2 images from September 2025 and September 2026.

The coverage check found newer product versions to evaluate when the corresponding lessons are written: GEDI L2A and L2B v003, GEDI L4A V3, and ECOSTRESS LSTE v003.

## Execution platforms

Some CHPC compute nodes cannot reach the internet. OnDemand sessions on the default interactive partition could in our tests (2026-11-04), but CHPC documents interactive compute sessions as offline, and many batch partitions are. Every lesson that retrieves remote data must therefore work in two stages that use the same notebook: a run with internet access fills the cache, and any later run, including one on an offline node, reuses it. [The CHPC guide](getting-started/chpc.md) describes the transfer job that fills the cache when a session is offline. Colab and local runs do both stages in one pass.

## Validation checklist

A lesson is ready for learners when all of the following hold. Record each run in the lesson README and the tutorial index.

- [ ] It runs from a fresh kernel, top to bottom, using the documented environment and only the stated prerequisites.
- [ ] A second run reuses the cache, and an offline run (`TFS_OFFLINE=1`) completes from the cache.
- [ ] Empty searches, missing credentials, offline runs without a cache, and results with no valid pixels each produce a clear message.
- [ ] Units, dimensions, coordinate reference systems, coverage, and valid-observation counts are sensible. A known pixel or footprint is checked against the source data or an independent calculation.
- [ ] Python and R versions agree within a stated tolerance where both exist (`scripts/compare_outputs.py` for raster results, `scripts/compare_footprints.py` for GEDI footprints).
- [ ] The map and plot have readable labels, units, and legends, with a saved static figure.
- [ ] Download size, runtime, peak memory, product version, and validation date are recorded for each platform tested.
- [ ] `pytest tests/` passes: no credentials, personal paths, or notebook outputs in committed files.
- [ ] References, dataset citations, and upstream attribution ([upstream-resources.md](upstream-resources.md)) are present.

Each language and platform combination is marked tested (with date and environment) or untested. Do not add an Open in Colab link or a CHPC command until it has run successfully on that platform.

## Git

- Add files individually and write descriptive commit messages.
- Strip notebook outputs before committing (`nbstripout <notebook>`).
- Never commit data, caches, outputs, credentials, or machine-specific configuration.
