#!/bin/bash
#SBATCH --job-name=tfs-notebook
#SBATCH --partition=notchpeak-dtn
#SBATCH --qos=notchpeak-dtn
#SBATCH --account=dtn
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out
#
# Run a Trees from Space notebook on a CHPC data transfer node (DTN).
#
# Compute nodes, including OnDemand Jupyter sessions, cannot reach the
# internet. This job runs the saved notebook, with its own settings, on a node
# that can, so the data it fetches land in the lesson cache. Then rerun the
# notebook in OnDemand: cells that fetch data find the cache and skip the
# network. The partition, QOS, and account above are CHPC's public data
# transfer settings, so the job does not use your group's allocation.
#
# Submit from the repository root (Slurm does not create the log folder):
#   mkdir -p logs
#   sbatch scripts/slurm/notebook-dtn.sbatch tutorials/<topic>/<topic>-python.ipynb
#
# Environment prefixes default to ~/envs/tfs-python and the registered
# tfs-r kernel; override with TFS_PYTHON_ENV or TFS_R_KERNEL before sbatch.
# Set TFS_CACHE_DIR / TFS_OUTPUT_DIR in the submitting shell to use the same
# folders as your OnDemand session.
# Contributors: TFS_RECORD=1 sbatch ... runs the notebook through
# scripts/validate_notebook.py and records the result.

set -euo pipefail

NOTEBOOK="${1:?usage: sbatch scripts/slurm/notebook-dtn.sbatch <notebook.ipynb>}"
REPO="${SLURM_SUBMIT_DIR:-$PWD}"
cd "$REPO"
if [[ ! -f .tfs-root ]]; then
    echo "error: submit from the trees-from-space repository root" >&2
    exit 2
fi
if [[ ! -f "$NOTEBOOK" ]]; then
    echo "error: notebook not found: $NOTEBOOK" >&2
    exit 2
fi

# A clean environment: CHPC modules can shadow the environment's libraries.
module purge 2>/dev/null || true
TFS_PYTHON_ENV="${TFS_PYTHON_ENV:-$HOME/envs/tfs-python}"
export PATH="$TFS_PYTHON_ENV/bin:$PATH"
export PYTHONNOUSERSITE=1
# What `conda activate` would set; without PROJ_DATA, GDAL-based readers
# report "proj_create_from_database: Open of .../share/proj failed".
export GDAL_DATA="$TFS_PYTHON_ENV/share/gdal"
export PROJ_DATA="$TFS_PYTHON_ENV/share/proj"

case "$NOTEBOOK" in
    *-r.ipynb) KERNEL="${TFS_R_KERNEL:-tfs-r}" ;;
    *) KERNEL=python3 ;;  # the Python of the environment put on PATH above
esac

mkdir -p logs/notebooks
name="$(basename "${NOTEBOOK%.ipynb}")"
executed="logs/notebooks/${name}-${SLURM_JOB_ID:-manual}.ipynb"

echo "job=${SLURM_JOB_ID:-none} partition=${SLURM_JOB_PARTITION:-none} started=$(date -Is)"
echo "notebook=$NOTEBOOK kernel=$KERNEL"
if [[ "${TFS_RECORD:-0}" == "1" ]]; then
    # Validation mode: run through the validator, which prints a JSON record
    # (runtime, memory, data read, summary) and saves it under validation/.
    python scripts/validate_notebook.py "$NOTEBOOK" --label dtn --record \
        --executed-dir logs/notebooks
else
    papermill --kernel "$KERNEL" --cwd "$(dirname "$NOTEBOOK")" \
        --log-output --no-progress-bar "$NOTEBOOK" "$executed"
    echo "executed copy: $executed"
fi
echo "finished=$(date -Is)"
