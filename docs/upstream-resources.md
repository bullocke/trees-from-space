# Upstream resources

This page records the external tutorials, guides, and repositories that informed each lesson. The lessons do not bundle upstream notebooks. Where a lesson follows an upstream example, the table below names the exact file, the commit inspected, its license, and how the lesson differs.

Optional local checkouts of these repositories belong in the ignored `references/` directory. A published lesson must run from this repository and its documented environments alone.

## Repositories inspected

Commits were read on 2026-11-03 with `git ls-remote`. None of the upstream workflows were executed for this project.

| Repository | Commit | License | Files inspected | Used for |
| --- | --- | --- | --- | --- |
| [nasa/HLS-Data-Resources](https://github.com/nasa/HLS-Data-Resources) | `3ac8d6a3e47df95ab3a239e9a474da8a682df503` | Apache-2.0 | `python/tutorials/HLS_Tutorial.ipynb`, `r/HLS_Tutorial.Rmd`, `README.md` | HLS lesson design (Python and R) |
| [nasa/GEDI-Data-Resources](https://github.com/nasa/GEDI-Data-Resources) | `3a793323274c04b4d226009014dbc01a5d252a11` | Apache-2.0 | `README.md` | Anticipating GEDI environment needs |
| [ASFOpenSARlab/NISAR_Cookbook](https://github.com/ASFOpenSARlab/NISAR_Cookbook) | `34996e5e7e748ea74666f287398e222f11079197` | Apache-2.0 | `LICENSE` | Anticipating NISAR environment needs |
| [microsoft/PlanetaryComputerExamples](https://github.com/microsoft/PlanetaryComputerExamples) | `61026bcd725387944f189bc4873f76bda51c2268` | MIT | `LICENSE` | Considered for the STAC lesson; Earth Search chosen instead (no signing step) |
| [boettiger-lab/earthdatalogin](https://github.com/boettiger-lab/earthdatalogin) | CRAN 0.0.5 (2026-06-19) | MIT | `NAMESPACE`, `R/edl_search.R`, `R/edl_netrc.R` | Evaluated for R access; not used (see below) |

## HLS vegetation map (`tutorials/hls-vegetation-map/`)

The lesson's code is original. It follows the overall workflow of the NASA LP DAAC HLS tutorials: search CMR for HLSL30 and HLSS30 v2.0, select NIR, red, and Fmask, apply scale factors and quality masks, compute a vegetation index, and save a Cloud Optimized GeoTIFF. It departs from them in these ways:

- **TLS verification stays on.** Both upstream tutorials set `GDAL_HTTP_UNSAFESSL=YES`, which disables certificate checks. The lessons never set it, and `tests/test_repo_rules.py` rejects it.
- **Scale factors are read, not assumed.** The upstream Python tutorial hard-codes 0.0001. The lessons read the scale and offset stored with each band and fall back to the documented value only with a visible note. The upstream R tutorial takes the same approach.
- **The study area decides which scene to use.** The lessons rank granules by the clear-pixel fraction inside the study area rather than by tile-wide cloud cover, and they read only the study-area window of each file.
- **Maps are static.** Matplotlib (Python) and `terra::plot` (R) replace the hvplot and dygraphs widgets, so the figures render the same way on CHPC, in Colab, and on GitHub.
- **The R lesson searches NASA's STAC catalog and uses the learner's own credentials.** The upstream R tutorial uses rstac with NASA's CMR-STAC endpoint and `earthdatalogin` for authentication. The lesson keeps rstac and CMR-STAC, which returned the same granules as the Python lesson's `earthaccess` search, but does not use `earthdatalogin`. Its `edl_search()` is documented as an unsupported fallback, and both `edl_search()` and `edl_netrc()` write a shared public Earthdata account when they find no credentials at the package's own netrc path. The R lesson instead points GDAL at `~/.netrc` through environment variables and copies study-area windows with GDAL's `translate` tool (`sf::gdal_utils()`), which keeps the stored values and metadata. The resulting cache files are identical to those the Python lesson writes, so the two lessons share a cache.

## Sentinel-2 through STAC (`tutorials/sentinel2-stac/`)

The lesson's code is original. No upstream notebook was adapted. The design follows the brief's guidance for the introductory STAC lesson: one tested provider without paid services, an explanation of collections, items, and assets, a check of asset access requirements, and a small raster window. Earth Search (Element 84) was chosen over Microsoft's Planetary Computer because its files need no signing step, its links do not expire, and it charges readers nothing (`storage:requester_pays` is false). Findings while building the lesson, checked on 2026-11-04:

- **Use Collection 1 (`sentinel-2-c1-l2a`).** In the older `sentinel-2-l2a` collection, items flagged `earthsearch:boa_offset_applied: true` still list `offset: -0.1` in `raster:bands`, although the stored values already have the offset removed (a dense-forest red pixel is stored as 326, which is 0.0326 in reflectance). Applying the catalog's offset there gives negative reflectance. In Collection 1, the same pixel is stored as 1326, and both the catalog and the file give scale 0.0001 and offset −0.1.
- **Citation.** The Collection 1 record's `cite-as` link is `doi:10.5270/S2_-742ikth`, which resolves to ESA's *Level-1C* TOA product. The lesson cites the Level-2A product, `doi:10.5270/S2_-znk9xsj`.

## GEDI canopy height (`tutorials/gedi-canopy-height/`)

The lesson's code is original. It uses NASA's [GEDI data resources](https://github.com/nasa/GEDI-Data-Resources) (commit `3a793323274c04b4d226009014dbc01a5d252a11`, Apache-2.0) and the [GEDI L2A version 3 user guide](https://lpdaac.usgs.gov/documents/2442/GEDI02_User_Guide_V3.pdf) for product structure and quality guidance, and NASA's [Harmony](https://harmony.earthdata.nasa.gov/docs) service for subsetting: through `harmony-py` in Python, and through Harmony's web interface with `httr2` in R, which also searches the [CMR search API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) directly. Findings checked on 2026-11-04:

- **Version 3 is current.** `GEDI02_A` v002 is marked complete (data to July 2025); v003 is active, with improved geolocation and consistent quality flags.
- **Quality flag names changed.** v003 beam groups contain `l2a_quality_flag_rel3` and `l2a_quality_flag_rel2`, not `quality_flag`. The rel3 flag requires sensitivity above 0.95 over land (0.98 in tropical forest).
- **Harmony supports GEDI L2A** (both versions) through its trajectory subsetter: spatial, temporal, and variable subsets, HDF5 output. Variables are named by full path for each beam (for example `/BEAM0101/rh`). A request for 19 granules with 88 variables returned 13 files totaling 4.9 MB. Jobs took between 1 and 10 minutes. Granules with no footprints in the box produce warnings and no file. Output files are named `<work item>_<granule>_subsetted.h5`.
- **Harmony from R.** The R lesson sends the same request that `harmony-py` sends: a multipart form posted to `/<collection>/ogc-api-coverages/1.0.0/collections/parameter_vars/coverage/rangeset`, with `subset=lat(...)`, `subset=lon(...)`, a comma-separated `granuleId`, one `variable` field per variable, and `forceAsync=true`. A first GET of `/jobs` follows the Earthdata Login redirects and stores Harmony's session cookie; job status is `/jobs/<id>`, and result files are the `links` with `rel = "data"` (paged with `rel = "next"`). R's `curl` package must be told `httpauth = 1` (basic): its default lets libcurl wait for a challenge that Earthdata Login never sends, so the `~/.netrc` credentials are never offered and the login page comes back instead. Command-line `curl --netrc` does not have this problem.
- **Reading with hdf5r.** hdf5r reverses HDF5 dimensions, so `rh` (footprints by 101 percentiles in the file) arrives as a 101-row matrix with one column per footprint, and RH98 is row 99. `shot_number` (unsigned 64-bit) arrives as `bit64::integer64`, which keeps it exact.
- **Fidelity.** `scripts/check_gedi_subset.py` compares Harmony's subsets with the original granules, read remotely with `earthaccess.open` and `h5py`; shot numbers, positions, RH98, and flags were identical.

## NISAR backscatter and change (`tutorials/nisar-backscatter/`)

The lesson's code is original. No upstream notebook was adapted, and the NISAR Cookbook listed above was not used for code. Product structure comes from the files themselves (dataset descriptions and attributes read with `h5py`) and from the [ASF NISAR documentation](https://nisar-docs.asf.alaska.edu/). The HDF5 paths and the remote-window approach (coordinate arrays, then a hyperslab read through `earthaccess`'s HTTPS session) follow [nice-sar](https://github.com/bullocke/nice-sar) (MIT), a NISAR library by this project's author, with one change: the lesson transforms all four corners of the study box into the map projection, not two. Findings checked on 2026-11-04 are listed in the [lesson README](../tutorials/nisar-backscatter/README.md#products-and-references). In brief:

- **Maturity.** Beta GCOV is uncalibrated; for the same acquisition (2026-01-09, track 172), its HV median over the `cowlitz` box is 1.44 dB below the provisional value.
- **Search completeness.** For one box, CMR's UMM-JSON search (used by `earthaccess`) returned 69 of 72 GUNW provisional granules that CMR reported as hits; CMR's JSON search returned all 72.
- **Remote reads.** With 1 MB `fsspec` blocks, reading HH, HV, and the mask for a 6.6 km box moves about 15 MB per 7 GB file in about 10 s; smaller blocks move less but take longer.

## Data and product documentation

| Product | Reference |
| --- | --- |
| HLSL30 v2.0 | Masek, J. et al. HLS Operational Land Imager Surface Reflectance and TOA Brightness Daily Global 30m v2.0. NASA EOSDIS LP DAAC. [doi:10.5067/HLS/HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002) |
| HLSS30 v2.0 | Masek, J. et al. HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance Daily Global 30m v2.0. NASA EOSDIS LP DAAC. [doi:10.5067/HLS/HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002) |
| HLS user guide | [HLS Product User Guide, version 2.0](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf) |
| Sentinel-2 L2A | European Space Agency (2022). Sentinel-2 MSI Level-2A BOA Reflectance [Data set]. [doi:10.5270/S2_-znk9xsj](https://doi.org/10.5270/S2_-znk9xsj) |
| GEDI L2A v003 | Dubayah, R., Hofton, M., Blair, J., Armston, J., Tang, H., and Luthcke, S. (2026). GEDI L2A Elevation and Height Metrics Data Global Footprint Level V003. NASA LP DAAC. [doi:10.5067/GEDI/GEDI02_A.003](https://doi.org/10.5067/GEDI/GEDI02_A.003) |
| NISAR GCOV, provisional | NASA/JPL/NISAR (2026). NISAR Provisional Geocoded Polarimetric Covariance Product (Version 1). NASA Alaska Satellite Facility DAAC. [doi:10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1) |
| NISAR GUNW, provisional | NASA/JPL/NISAR (2026). NISAR Provisional Geocoded Unwrapped Interferogram Product (Version 1). NASA Alaska Satellite Facility DAAC. [doi:10.5067/NIL2GUNW-P1](https://doi.org/10.5067/NIL2GUNW-P1) |
| NISAR documentation | [ASF NISAR documentation](https://nisar-docs.asf.alaska.edu/); [NISAR Science Users' Handbook](https://doi.org/10.48577/jpl.UD4HV3) |
