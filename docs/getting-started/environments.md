# Environments and kernels

An **environment** is a self-contained folder of software: a specific version of Python or R plus the packages a lesson needs. Using the project's environments means every learner runs the same software that was used to test the lessons. A **kernel** is how Jupyter starts an environment's Python or R behind a notebook.

The project has two environments, defined in `environments/`:

| Environment | File | Used by |
| --- | --- | --- |
| `tfs-python` | `python-base.yml` | Python lessons, plus Jupyter and papermill for running notebooks on CHPC |
| `tfs-r` | `r-base.yml` | R lessons |

Each file lists packages with loose version limits. The matching `*.lock.txt` files record the exact versions used in the most recent successful validation and can recreate that environment on 64-bit Linux, the platform of CHPC and Colab.

## Creating the environments

You need a conda-compatible package manager: `mamba` or `conda` from [Miniforge](https://github.com/conda-forge/miniforge), or `micromamba`. On CHPC, load Miniforge as a module (see the [CHPC guide](chpc.md)). Create each environment in a folder you choose, called its **prefix**:

```bash
git clone https://github.com/bullocke/trees-from-space.git
cd trees-from-space
mamba env create -p ~/envs/tfs-python -f environments/python-base.yml
mamba env create -p ~/envs/tfs-r -f environments/r-base.yml   # R lessons only
```

Python lessons need only `tfs-python`. Creating an environment downloads about 1 GB of packages and takes several minutes.

To reproduce the exact validated versions instead, create the environment from a lockfile:

```bash
mamba create -p ~/envs/tfs-python --file environments/python-base.linux-64.lock.txt
```

## Registering the kernels

Register the environments as Jupyter kernels once, from the repository folder:

```bash
~/envs/tfs-python/bin/python scripts/install_kernels.py --r-prefix ~/envs/tfs-r
```

Leave out `--r-prefix ~/envs/tfs-r` if you did not create the R environment. The kernels then appear as **Python 3.12 (Trees from Space)** and **R 4.5 (Trees from Space)** in JupyterLab, OnDemand, and VS Code. The script also records where each environment keeps its geospatial reference data (GDAL and PROJ), which kernels otherwise cannot find reliably.

## Moving data, cache, and output folders

By default, lessons write inside the repository: `data/` for inputs you provide, `cache/` for downloaded data, and `outputs/` for results. Git ignores all three. To use other locations, such as scratch storage on CHPC, set these environment variables before starting Jupyter or submitting a batch job:

| Variable | Default | Holds |
| --- | --- | --- |
| `TFS_DATA_DIR` | `<repository>/data` | Your own input files |
| `TFS_CACHE_DIR` | `<repository>/cache` | Downloaded data that can be fetched again |
| `TFS_OUTPUT_DIR` | `<repository>/outputs` | Lesson results |

In Colab, the defaults are folders under `/content`.

## Updating or removing an environment

New lessons sometimes add packages to the specification; each lesson's README says when. The quickest way to add them is to update the environment in place:

```bash
mamba env update -p ~/envs/tfs-python -f environments/python-base.yml
mamba env update -p ~/envs/tfs-r -f environments/r-base.yml   # R lessons only
```

mamba lists the changes and waits for you to type `y` before applying them. The getting-started notebooks report any package that is still missing.

For results you need to reproduce exactly, remove the environment and create it again instead, from the specification or from the lockfile. Updates in place can leave versions that differ from the ones the lessons were tested with.

```bash
mamba env remove -p ~/envs/tfs-python
jupyter kernelspec remove tfs-python
```
