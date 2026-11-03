# Running on your own computer

The lessons run on a laptop or workstation with Linux, macOS, or Windows through the Windows Subsystem for Linux (WSL). They use small study areas, so 8 GB of memory and a few hundred megabytes of free disk space are enough. You need an internet connection for the steps that search for and retrieve data.

## Setup

1. Install [Miniforge](https://github.com/conda-forge/miniforge), which provides `mamba` and `conda`. If you already use `micromamba`, use it in place of `mamba` in the commands below.
2. Create the environments and register the kernels as described in the [environment guide](environments.md).
3. Create your `~/.netrc` as described in the [Earthdata Login guide](earthdata-login.md).

## JupyterLab

Start JupyterLab from the repository folder with the Python environment active:

```bash
mamba activate ~/envs/tfs-python
cd trees-from-space
jupyter lab
```

JupyterLab opens in your browser. Open a lesson from `tutorials/` and choose the Trees from Space kernel when prompted.

## VS Code

1. Install the Python and Jupyter extensions.
2. Open the repository folder (*File → Open Folder*).
3. Open a lesson notebook, click the kernel picker in the upper right corner, and choose **Python 3.12 (Trees from Space)** or **R 4.5 (Trees from Space)**. If the kernels are missing, choose *Select Another Kernel → Jupyter Kernel* and refresh, or check that you ran `scripts/install_kernels.py`.

On WSL, open the folder through the WSL extension (*Remote Explorer → WSL*) so that VS Code uses the Linux environment, not a Windows Python installation.
