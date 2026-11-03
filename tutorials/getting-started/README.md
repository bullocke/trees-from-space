# Getting started: check your setup

| | |
| --- | --- |
| **Notebooks** | [`getting-started-python.ipynb`](getting-started-python.ipynb) · `getting-started-r.ipynb` (planned) |
| **You will** | Confirm the environment, writable folders, network access, and Earthdata credentials, and save a report |
| **Prerequisites** | An environment and kernel ([environment guide](../../docs/getting-started/environments.md)); an Earthdata account and `~/.netrc` ([Earthdata Login guide](../../docs/getting-started/earthdata-login.md)) |
| **Data** | None downloaded. When online, the notebook opens the header of one HLS file to test data access. |
| **Time** | About 5 minutes |
| **Output** | `outputs/getting-started/environment-report-python.json` |

Run this notebook on every platform you plan to use. On CHPC, its network check tells you whether you are on a machine that can download data or on a compute node that needs the transfer-job route described in the [CHPC guide](../../docs/getting-started/chpc.md).

The report contains no usernames, passwords, hostnames, or personal paths, so you can share it when asking for help.

## Validation record

| Date | Platform | Language | Network | Result | Runtime | Peak memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-03 | Local (WSL, Ubuntu 22.04) | Python 3.12.16 | Online | Passed: login and data access OK | 12 s | 210 MB | earthaccess 0.19.0, rasterio 1.5.0, GDAL 3.12.4 |
| 2026-11-03 | Local (WSL), `TFS_OFFLINE=1` | Python 3.12.16 | Offline (simulated) | Passed: network checks skipped with guidance | 6 s | 197 MB | Simulates a CHPC compute node |

Full records are in [`validation/`](validation/).
