# Forest change from NISAR radar backscatter and coherence

[![Open the Python notebook in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bullocke/trees-from-space/blob/main/tutorials/nisar-backscatter/nisar-backscatter-python.ipynb)

| | |
| --- | --- |
| **Notebook** | [`nisar-backscatter-python.ipynb`](nisar-backscatter-python.ipynb) |
| **Question** | Where and when was forest cut near Pigeon Springs, Washington, during NISAR's first year of calibrated data, and how can radar tell a harvest from a seasonal change? |
| **You will** | Find NISAR GCOV and GUNW granules with `earthaccess` and read their names (maturity, track, direction, frame); read a 6.6 km window from 7 GB HDF5 files over HTTPS with `h5py`, without downloading them; map HH, HV, and a color composite in dB; build a year-long backscatter series on one stack, flag forest patches whose HV dropped, and date each change; use 12-day interferometric coherence to separate harvested forest from young stands |
| **Prerequisites** | [Getting started](../getting-started/); an Earthdata Login in `~/.netrc`. No packages beyond the project environment. |
| **Data** | NISAR L2 GCOV and GUNW, provisional release (track 172, descending, frame 65): 28 GCOV and 26 GUNW granules (about 245 GB in full), plus one beta GCOV granule. The lesson moves about 0.7 GB over the network on its first run and caches about 40 MB. |
| **Time** | About 60 minutes of learner time in three parts, plus about 8 minutes of data reading on the first run |
| **Outputs** | `outputs/nisar-backscatter/python/`: backscatter map (COG, 10 m), change map with HV change, winter coherence, harvest patches, and change dates (COG, 20 m), backscatter and coherence time series and a patch table (CSV), figure (PNG), provenance (JSON) |
| **Level** | Intermediate |

![Expected result: NISAR harvest patches colored by date, winter coherence, and time series for harvested forest, a young stand, and stable forest](figures/expected-nisar.png)

This lesson introduces imaging radar through NASA's NISAR mission. Part A reads one GCOV image and explains backscatter, polarization, decibels, speckle, and terrain correction. Part B reads the same window from every date of one stack, a year of images 12 days apart, and flags forest whose HV backscatter dropped. Backscatter alone flags two kinds of places: stands that were clearcut, and young stands whose backscatter falls every dry season. Part C reads 12-day coherence from the GUNW products and uses winter coherence, which is low over tall forest, to separate the two.

The lesson reads only the chunks of each HDF5 file that overlap the study box. `h5py` opens each file through `earthaccess`'s authenticated HTTPS session (an `fsspec` file with 1 MB blocks), so no subsetting service or whole-file download is involved. Each window is cached as a small GeoTIFF, and later runs, including offline runs, use the cache.

## Study site

The lesson uses a third study site, `cowlitz`, added to [`examples/sites.geojson`](../../examples/sites.geojson) for it: a 6.6 km box of managed conifer forest near Pigeon Springs, Cowlitz County, Washington (tile T10TES). Neither shared site lost forest during NISAR's first year. Wind River's old-growth backscatter is nearly flat all year, and Pando's provisional record starts only in June 2026. The `cowlitz` box lies on the same NISAR stack as Wind River, about 50 km to the west, so the notebook's first exercise switches to Wind River by changing only the site settings.

We chose the box on 2026-11-04 by reading NISAR's 80 m frequency B layer for all 28 dates over about 95 by 90 km around Wind River. That screen found about 150 forest patches with a step drop in HV. The chosen box held the most strong drops, and they matched NDVI losses between Sentinel-2 images from September 2025 and September 2026 (see the checks below).

## Products and references

| Product | Version | Access route | Documentation |
| --- | --- | --- | --- |
| NISAR L2 Geocoded Polarimetric Covariance (GCOV), provisional | `NISAR_L2_GCOV_PROVISIONAL_V1` (`C2854338529-ASF`), product version 1.0.11 | `earthaccess` search; `h5py` over HTTPS (`earthaccess.get_fsspec_https_session()`) | [doi:10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1); [ASF NISAR documentation](https://nisar-docs.asf.alaska.edu/) |
| NISAR L2 Geocoded Unwrapped Interferogram (GUNW), provisional | `NISAR_L2_GUNW_PROVISIONAL_V1` (`C2854335566-ASF`) | as above | [doi:10.5067/NIL2GUNW-P1](https://doi.org/10.5067/NIL2GUNW-P1) |
| NISAR L2 GCOV, beta (one granule, for comparison) | `NISAR_L2_GCOV_BETA_V1` (`C3622214170-ASF`) | as above | [ASF NISAR documentation](https://nisar-docs.asf.alaska.edu/) |

**Findings while building the lesson** (checked 2026-11-04):

- **NISAR products are at ASF, not LP DAAC.** HTTPS links have the form `https://nisar.asf.earthdatacloud.nasa.gov/NISAR/<collection>/<granule>/<granule>.h5`. A GCOV granule is 6.5 to 7.2 GB and a GUNW granule about 2.3 GB.
- **Remote windows are practical.** GCOV layers are stored in 512 by 512 chunks with gzip compression. Reading HH, HV, and the mask for the box takes about 10 s and moves about 15 MB, much of it the coordinate arrays and the file's index, because each request returns a whole 1 MB block. Blocks of 256 KB moved 11 MB but took about twice as long, because each request has its own delay. The 10 m map date (five layers) moves about 24 MB, and a GUNW coherence window about 9 MB.
- **Beta and provisional releases differ.** The 2026-01-09 acquisition exists in both releases; over the box, the beta HV median is 1.44 dB lower than the provisional one. The lesson uses provisional products only.
- **Masks.** The GCOV `mask` is 0 for pixels made from partly invalid radar samples, 255 outside the swath, and otherwise the subswath number. The GUNW `mask` is a 32-bit integer: bits 0 to 7 hold three decimal digits (water flag, reference subswath, secondary subswath; a 0 subswath digit means invalid), bits 8 to 15 and 16 to 23 hold anomaly flags for the secondary and reference images. The two pairs that include 2026-04-15 carry an anomaly flag; the lesson keeps them and marks them in its coherence plot.
- **Grids line up.** GCOV (10 m) and GUNW (20 m) pixel edges fall on multiples of 20 m in the same UTM zone, so 2 by 2 averages of GCOV match the GUNW grid exactly when the window starts on a 20 m edge. The notebook checks this for every file.
- **One GUNW pair is missing from `earthaccess` searches.** For the `cowlitz` box, CMR's UMM-JSON search (which `earthaccess` uses) reported 72 GUNW hits but returned 69 records; CMR's JSON search returned all 72. The pair 2026-07-08 to 2026-07-20 on track 172 is one of the three, so the lesson has 26 pairs instead of 27. GCOV searches were complete.
- **Search filters.** Granule names give the polarization code: `DH` means HH and HV, `SH` HH only. The lesson keeps one granule per date: the full frame and the highest product counter where NASA reprocessed a date.

## Support status

| Language | Local (Linux/WSL) | CHPC OnDemand, compute node | CHPC transfer job | Colab |
| --- | --- | --- | --- | --- |
| Python | tested 2026-11-04 | tested 2026-11-05 | untested (optional) | tested 2026-11-05 |

## Validation record

| Date | Platform | Language | Run | Result | Runtime | Peak kernel memory | New data cached | Harvest patches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-04 | Local (WSL, Ubuntu 22.04) | Python 3.12.16 | Cold (empty cache): 55 files read remotely, 692 MB transferred | Passed | 439 s | 733 MB | 42.1 MB | 14 (154 ha) |
| 2026-11-04 | Local (WSL, Ubuntu 22.04) | Python 3.12.16 | Warm (cache) | Passed | 20 s | 593 MB | 0.00 MB | 14 (154 ha) |
| 2026-11-04 | Local (WSL, Ubuntu 22.04) | Python 3.12.16 | Offline (`TFS_OFFLINE=1`) | Passed | 15 s | 592 MB | 0.00 MB | 14 (154 ha) |
| 2026-11-05 | CHPC OnDemand, compute node (`notchpeak-shared-short`) | Python 3.12.16 | Cold (empty cache): 55 files, 692 MB transferred | Passed | 466 s | 732 MB | 42.1 MB | 14 (154 ha) |
| 2026-11-05 | Colab (fresh session) | Python 3.13.18 | Cold (empty cache): 55 files, 692 MB transferred | Passed | 1,011 s, excluding package installation | not recorded | not recorded | 14 (154 ha) |

**Checks of the result** (2026-11-04, local; [`validation/2026-11-04-local-python-checks.json`](validation/2026-11-04-local-python-checks.json), from `scripts/check_nisar_lesson.py`):

- **Known pixels.** For 50 random pixels of the 10 m HV map, the value read directly from the original GCOV file at the same longitude and latitude (located with the file's own coordinate arrays) agreed within 1e-6 dB.
- **Aggregation.** For 60 random 20 m blocks on 3 dates, the 2 by 2 means recomputed from the original 10 m HH, HV, and mask were identical to the cached values.
- **Coherence.** For 3 pairs, the lesson's 20 m coherence averaged to 80 m had a rank correlation of 0.94 to 0.98 with the GUNW 80 m coherence layer; medians differed by 0.01 to 0.02.
- **Sentinel-2.** Between Sentinel-2 L2A images of 16 September 2025 and 16 September 2026 (tile T10TES), NDVI fell by a median of 0.50 in the harvest patches, and every one of the 14 patches lost more than 0.2. Patches that backscatter flagged but winter coherence set aside showed no loss (median +0.05), and unchanged pixels changed by −0.005. The harvest patches contain 67% of the pixels where NDVI fell by more than 0.3 from above 0.8; the remainder was not examined further.
- **Other sites.** With `SITE_ID = "wref"` (same stack), the run passed and found no harvest; its box median HV fell from −9.27 to −11.96 dB on 2026-01-21 and recovered 12 days later. With `SITE_ID = "pando"` and `STACK = None`, the run used stack `157_D_069` (10 dates from 2026-06-25) and passed with no harvest and no winter pairs.
- **Failure messages.** Offline with an empty cache, and a date window before NISAR's record, each stop with a message that says what to do.

The CHPC and Colab runs gave the same granules, patches, and summary values as the local runs. The CHPC record shows `2578a51-dirty` because of local changes in that clone; the notebook there was unchanged since it was committed. Colab used pandas 2.2.3 and h5py 3.14.0 rather than the project environment's versions, with identical results, and its data reading took about twice as long as on CHPC or locally.

Full records, with the commit and package versions, are in [`validation/`](validation/). Records of CHPC and Colab runs come from the printed output of `scripts/validate_notebook.py` without `--record`. The environment is described by [`environments/python-base.linux-64.lock.txt`](../../environments/python-base.linux-64.lock.txt).
