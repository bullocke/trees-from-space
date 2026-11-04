# Running on CHPC

The University of Utah [Center for High Performance Computing](https://www.chpc.utah.edu/) (CHPC) is the main platform for these lessons. This page covers one-time setup, how to run a lesson, and where files live. It assumes you have a CHPC account and can log in to [Open OnDemand](https://ondemand.chpc.utah.edu/), CHPC's browser portal.

> **Note:** This has not been endorsed by the University of Utah or the CHPC. I followed CHPC guidance in development and have done my best to ensure good practices, but use at your own risk. When in doubt, consult CHPC documentation or support. I hope to have this fully validated by the CHPC technical team soon.

## Which machines can reach the internet

CHPC has several kinds of machines, and they differ in one way that matters for these lessons: whether they can download data.

| Machine | What it is for | Internet access |
| --- | --- | --- |
| **Login node** (e.g. `notchpeak1`) | Editing files, installing software, submitting jobs. No heavy computation. | Yes |
| **OnDemand session** on `notchpeak-shared-short`, the default partition for interactive apps | Running the lessons in Jupyter | Yes, in our tests on 2026-11-04 |
| **Other compute nodes** (batch jobs, owner partitions) | Jobs scheduled through Slurm | Often no |
| **Data transfer node** (DTN) | Moving data, through Slurm jobs on the `notchpeak-dtn` partition | Yes, with fast connections |

CHPC's [OnDemand documentation](https://www.chpc.utah.edu/documentation/software/ondemand.php) states that interactive sessions on compute nodes do not have direct internet access, and batch jobs on some compute partitions time out when they try to download. In our tests, however, OnDemand Jupyter sessions on the default `notchpeak-shared-short` partition searched NASA's catalog and downloaded lesson data without help. Because access can differ between partitions and can change, the lessons check it every time they run. They also keep everything they download in a **cache**: once any run with internet access has saved the study-area data, later runs read the saved copy, even on a node that cannot reach the internet.

## One-time setup

Do these steps once, on a login node. Connect with `ssh <uNID>@notchpeak.chpc.utah.edu`, or open a shell from OnDemand (*Clusters → notchpeak Shell Access*).

1. **Get the lessons.** These steps clone into your home directory. If you clone somewhere else, such as your group space, use that folder wherever this page says `~/trees-from-space`.

   ```bash
   cd ~
   git clone https://github.com/bullocke/trees-from-space.git
   ```

2. **Create the environments.** Starting from a clean module list avoids library conflicts with CHPC modules. The package cache goes to scratch so that it does not fill your home directory.

   ```bash
   module purge
   module load miniforge3
   export CONDA_PKGS_DIRS=/scratch/general/vast/$USER/conda-pkgs
   cd ~/trees-from-space
   mamba env create -p ~/envs/tfs-python -f environments/python-base.yml
   mamba env create -p ~/envs/tfs-r -f environments/r-base.yml   # R lessons only
   ```

3. **Register the kernels.**

   ```bash
   ~/envs/tfs-python/bin/python scripts/install_kernels.py --r-prefix ~/envs/tfs-r
   ```

   Leave out `--r-prefix ~/envs/tfs-r` if you skipped the R environment.

4. **Store your Earthdata credentials** in `~/.netrc`, following the [Earthdata Login guide](earthdata-login.md). Login nodes have internet access, so Option A works there. Your home directory is shared by all CHPC machines, so OnDemand sessions and transfer jobs see the same file.

5. **Create a folder for batch logs.** Slurm does not create it for you.

   ```bash
   mkdir -p ~/trees-from-space/logs
   ```

## Starting Jupyter in OnDemand

1. In OnDemand, choose *Interactive Apps → Jupyter*.
2. Set **Jupyter Python version** to *Custom (Environment Setup below)* and enter these lines in **Environment Setup for Custom Python**, changing the last line if you cloned the repository somewhere else:

   ```bash
   export TFS_PYTHON_ENV=$HOME/envs/tfs-python
   export PATH=$TFS_PYTHON_ENV/bin:$PATH
   export GDAL_DATA=$TFS_PYTHON_ENV/share/gdal PROJ_DATA=$TFS_PYTHON_ENV/share/proj PYTHONNOUSERSITE=1
   test -x $TFS_PYTHON_ENV/bin/jupyter || echo "ERROR: no Jupyter in $TFS_PYTHON_ENV; check the environment path"
   cd ~/trees-from-space
   ```

   These lines put the environment's programs, including Jupyter, first on your `PATH`, and set the two data paths that `conda activate` would otherwise set. They do not rely on loading modules or on `conda activate`, which did not take effect in OnDemand's setup script in our tests. The transfer-job script uses the same approach.

3. Choose resources. For these lessons, 2 cores, 8 GB of memory, and 2 hours are plenty. The default cluster (`notchpeak`) and partition (`notchpeak-shared-short`) are designed for interactive work. Use your group's account.
4. Click **Launch**, wait for the session to start, and click **Connect to Jupyter**.

Run the [getting-started notebook](../tutorials/getting-started/) first. It reports whether your session can reach NASA and whether your credentials file is in place, which tells you how to run the lessons below.

## Running a lesson that downloads data

### If your session can reach NASA (the usual case)

Open the lesson and run it from top to bottom. The first run downloads the study-area data into the cache, and later runs reuse it.

### If your session is offline: fetch the data with a transfer job first

1. Open the lesson in OnDemand Jupyter and review the settings cell. If you change anything, save the notebook (*File → Save*), because the batch job reads the saved file.
2. From a terminal on a login node (or *File → New → Terminal* in Jupyter), submit the notebook to a data transfer node:

   ```bash
   cd ~/trees-from-space
   sbatch scripts/slurm/notebook-dtn.sbatch tutorials/hls-vegetation-map/hls-vegetation-map-python.ipynb
   ```

3. Check progress with `squeue --me`. The log is `logs/tfs-notebook-<jobid>.out`, and the job saves an executed copy of the notebook in `logs/notebooks/`. A small lesson usually takes a few minutes once the job starts.
4. When the job finishes, return to OnDemand and run the whole notebook (*Kernel → Restart Kernel and Run All Cells*). Cells that fetch data print `cached` and skip the network, and the analysis runs on the compute node.

The transfer job uses CHPC's public data transfer settings (`notchpeak-dtn` partition, `dtn` account), so it does not draw on your group's allocation.

## Storage

| Location | Path | Use for | Notes |
| --- | --- | --- | --- |
| Home | `~` | The repository, environments, `~/.netrc`, small caches and outputs | Backed up; limited quota |
| Group space | Ask your group | Results and reusable inputs you want to keep | Shared with your group |
| Scratch | `/scratch/general/vast/$USER` | Large caches and intermediate files | Files unused for 60 days are deleted; not backed up |

The introductory lessons download only a few megabytes, so the default `cache/` and `outputs/` folders inside the repository are fine. For larger lessons, put the cache on scratch by exporting `TFS_CACHE_DIR` in the OnDemand **Environment Setup** box and in the terminal before you run `sbatch`, so that both runs use the same folder:

```bash
export TFS_CACHE_DIR=/scratch/general/vast/$USER/trees-from-space/cache
```

To remove one lesson's cached data, delete only its folder:

```bash
rm -rf ~/trees-from-space/cache/hls
```

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| A cell reports that the machine cannot reach NASA and the cache lacks a file | The session has no internet access and the data have not been fetched yet | Fetch the data with a transfer job, as described above |
| `sbatch: error: ... logs/...` or a job with no log | The `logs/` folder does not exist | `mkdir -p ~/trees-from-space/logs` |
| The Jupyter session ends at once; its log says `jupyter: command not found` | The setup lines did not put the environment on `PATH` | Use the setup lines above exactly, with your environment's path. The log's `ERROR: no Jupyter` line means the path is wrong. |
| The kernel menu lacks the Trees from Space kernels | Kernels were not registered | Run step 3 of the one-time setup |
| Import errors or GDAL library errors | A CHPC module conflicts with the environment | Run `module purge` in your terminal before other commands. In OnDemand, use the setup lines above, which load no modules. |
| `Earthdata credentials not found` | No `~/.netrc` | Follow the [Earthdata Login guide](earthdata-login.md) |
