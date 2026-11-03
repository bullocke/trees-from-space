# Getting started: check your setup

| | |
| --- | --- |
| **Notebooks** | [`getting-started-python.ipynb`](getting-started-python.ipynb) · [`getting-started-r.ipynb`](getting-started-r.ipynb) |
| **You will** | Confirm the environment, writable folders, network access, and Earthdata credentials, and save a report |
| **Prerequisites** | An environment and kernel ([environment guide](../../docs/getting-started/environments.md)); an Earthdata account and `~/.netrc` ([Earthdata Login guide](../../docs/getting-started/earthdata-login.md)) |
| **Data** | None downloaded. When online, the notebook opens the header of one HLS file to test data access. |
| **Time** | About 5 minutes |
| **Output** | `outputs/getting-started/environment-report-python.json` (or `-r.json`) |

Run this notebook on every platform you plan to use. The R version checks data access through GDAL, which also confirms that NASA accepts your credentials; the Python version also logs in with `earthaccess`. On CHPC, its network check tells you whether you are on a machine that can download data or on a compute node that needs the transfer-job route described in the [CHPC guide](../../docs/getting-started/chpc.md).

The report contains no usernames, passwords, hostnames, or personal paths, so you can share it when asking for help.

## Validation record

| Date | Platform | Language | Network | Result | Runtime | Peak kernel memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-03 | Local (WSL, Ubuntu 22.04) | Python 3.12.16 | Online | Passed: login and data access OK | 10 s | 207 MB | earthaccess 0.19.0, rasterio 1.5.0, GDAL 3.12.4; commit c58dc42 |
| 2026-11-03 | Local (WSL), `TFS_OFFLINE=1` | Python 3.12.16 | Offline (simulated) | Passed: network checks skipped with guidance | 6 s | 197 MB | Simulates a CHPC compute node |
| 2026-11-03 | Local (WSL, Ubuntu 22.04) | R 4.5.3 | Online | Passed: data access OK | 6 s | 259 MB | terra 1.9.34, sf 1.1.0, GDAL 3.12.3; commit c58dc42 |
| 2026-11-03 | Local (WSL), `TFS_OFFLINE=1` | R 4.5.3 | Offline (simulated) | Passed: network checks skipped with guidance | 5 s | 252 MB | Simulates a CHPC compute node |

Full records are in [`validation/`](validation/).
