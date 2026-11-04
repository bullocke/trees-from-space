# Running on CHPC

The University of Utah [Center for High Performance Computing](https://www.chpc.utah.edu/) (CHPC) is the main platform for these lessons. This page covers one-time setup, how to run a lesson, and where files live. It assumes you have a CHPC account and can log in to [Open OnDemand](https://ondemand.chpc.utah.edu/), CHPC's browser portal.

> **Note:** This has not been endorsed by the University of Utah or the CHPC. I followed CHPC guidance in development and have done my best to ensure good practices, but use at your own risk. When in doubt, consult CHPC documentation or support. I hope to have this fully validated by the CHPC technical team soon.

## Which machines can reach the internet

CHPC has several kinds of machines, and they differ in one way that matters for these lessons: whether they can download data.

| Machine | What it is for | Internet access |
| --- | --- | --- |
| **Login node** (e.g. `notchpeak1`) | Editing files, installing software, submitting jobs. No heavy computation. | Yes |
| **Compute node** | Jobs scheduled through Slurm, **including OnDemand Jupyter and RStudio sessions** | **No** |
| **Frisco node** | Interactive and graphical work started from OnDemand | Yes, for downloads (CHPC calls these visualization nodes) |
| **Data transfer node** (DTN) | Moving data, through Slurm jobs on the `notchpeak-dtn` partition | Yes, with fast connections |

CHPC's [OnDemand documentation](https://www.chpc.utah.edu/documentation/software/ondemand.php) states that interactive sessions on compute nodes do not have direct internet access. A lesson that searches for and reads NASA data therefore cannot fetch that data from an ordinary OnDemand Jupyter session. The lessons handle this with a **cache**: once a run on a machine with internet access has saved the study-area data, every later run, including one on a compute node, reads the saved copy and skips the network. The two routes below differ only in where that first run happens.

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

4. **Store your Earthdata credentials** in `~/.netrc`, following the [Earthdata Login guide](earthdata-login.md). Login nodes have internet access, so Option A works there. Your home directory is shared by all CHPC machines, so compute nodes, Frisco nodes, and transfer jobs all see the same file.

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

The session runs on a compute node, so it has no internet access. Run the [getting-started notebook](../tutorials/getting-started/) first: it reports whether the node can reach NASA, whether your credentials file is in place, and which route below applies.

## Running a lesson that downloads data

### Route A (standard): fetch with a transfer job, then work in OnDemand

1. Open the lesson in OnDemand Jupyter and review the settings cell. If you change anything, save the notebook (*File → Save*), because the batch job reads the saved file.
2. From a terminal on a login node (or *File → New → Terminal* in Jupyter), submit the notebook to a data transfer node:

   ```bash
   cd ~/trees-from-space
   sbatch scripts/slurm/notebook-dtn.sbatch tutorials/hls-vegetation-map/hls-vegetation-map-python.ipynb
   ```

3. Check progress with `squeue --me`. The log is `logs/tfs-notebook-<jobid>.out`, and the job saves an executed copy of the notebook in `logs/notebooks/`. A small lesson usually takes a few minutes once the job starts.
4. When the job finishes, return to OnDemand and run the whole notebook (*Kernel → Restart Kernel and Run All Cells*). Cells that fetch data print `cached` and skip the network, and the analysis runs on the compute node.

The transfer job uses CHPC's public data transfer settings (`notchpeak-dtn` partition, `dtn` account), so it does not draw on your group's allocation.

### Route B (interactive): run everything on a Frisco node

Frisco nodes can reach the internet, so a Jupyter session there can run a lesson from start to finish without a separate transfer job. Choose a Frisco node as the cluster when you launch the Jupyter app, if your OnDemand menu offers one. Frisco nodes are shared by many users, so keep to the small lesson examples there and use Route A for larger requests.

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
| A cell waits, then reports that the network is unreachable | The notebook is running on a compute node with no cache yet | Use Route A or Route B above |
| `sbatch: error: ... logs/...` or a job with no log | The `logs/` folder does not exist | `mkdir -p ~/trees-from-space/logs` |
| The Jupyter session ends at once; its log says `jupyter: command not found` | The setup lines did not put the environment on `PATH` | Use the setup lines above exactly, with your environment's path. The log's `ERROR: no Jupyter` line means the path is wrong. |
| The kernel menu lacks the Trees from Space kernels | Kernels were not registered | Run step 3 of the one-time setup |
| Import errors or GDAL library errors | A CHPC module conflicts with the environment | Start the setup box and your terminal with `module purge` |
| `Earthdata credentials not found` | No `~/.netrc` | Follow the [Earthdata Login guide](earthdata-login.md) |
