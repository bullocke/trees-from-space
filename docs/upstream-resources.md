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
| [microsoft/PlanetaryComputerExamples](https://github.com/microsoft/PlanetaryComputerExamples) | `61026bcd725387944f189bc4873f76bda51c2268` | MIT | `LICENSE` | Planned STAC lesson |
| [boettiger-lab/earthdatalogin](https://github.com/boettiger-lab/earthdatalogin) | CRAN 0.0.5 (2026-06-19) | MIT | `NAMESPACE`, `R/edl_search.R`, `R/edl_netrc.R` | R authentication and search |

## HLS vegetation map (`tutorials/hls-vegetation-map/`)

The lesson's code is original. It follows the overall workflow of the NASA LP DAAC HLS tutorials: search CMR for HLSL30 and HLSS30 v2.0, select NIR, red, and Fmask, apply scale factors and quality masks, compute a vegetation index, and save a Cloud Optimized GeoTIFF. It departs from them in these ways:

- **TLS verification stays on.** Both upstream tutorials set `GDAL_HTTP_UNSAFESSL=YES`, which disables certificate checks. The lessons never set it, and `tests/test_repo_rules.py` rejects it.
- **Scale factors are read, not assumed.** The upstream Python tutorial hard-codes 0.0001. The lessons read the scale and offset stored with each band and fall back to the documented value only with a visible note. The upstream R tutorial takes the same approach.
- **The study area decides which scene to use.** The lessons rank granules by the clear-pixel fraction inside the study area rather than by tile-wide cloud cover, and they read only the study-area window of each file.
- **Maps are static.** Matplotlib (Python) and `terra::plot` (R) replace the hvplot and dygraphs widgets, so the figures render the same way on CHPC, in Colab, and on GitHub.
- **R authentication uses the learner's own credentials.** `earthdatalogin::edl_netrc()` writes a shared public account when called without arguments, so the R lesson points GDAL at `~/.netrc` directly.

## Data and product documentation

| Product | Reference |
| --- | --- |
| HLSL30 v2.0 | Masek, J. et al. HLS Operational Land Imager Surface Reflectance and TOA Brightness Daily Global 30m v2.0. NASA EOSDIS LP DAAC. [doi:10.5067/HLS/HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002) |
| HLSS30 v2.0 | Masek, J. et al. HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance Daily Global 30m v2.0. NASA EOSDIS LP DAAC. [doi:10.5067/HLS/HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002) |
| HLS user guide | [HLS Product User Guide, version 2.0](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf) |
