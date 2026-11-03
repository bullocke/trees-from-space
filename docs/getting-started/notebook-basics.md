# Notebook basics

The lessons are Jupyter notebooks: documents that mix explanatory text with code you run one piece at a time. This page covers what you need to follow a lesson. If you have used Jupyter before, skip to the [environment guide](environments.md).

## Cells, kernels, and order

A notebook is a sequence of **cells**. Text cells explain the next step, and code cells hold code you run. Running a code cell sends its code to the **kernel**, the Python or R process working behind the notebook, and shows the result underneath.

- Run the selected cell with **Shift + Enter**. The cursor moves to the next cell.
- The number in brackets next to a cell, such as `[3]`, shows the order in which cells ran. An asterisk, `[*]`, means the cell is still running.
- The kernel remembers everything that has run so far. A variable defined in one cell is available in later cells, but only after its cell has run.

Run the cells in order, from top to bottom. Most confusing errors come from running cells out of order or skipping one.

## Choosing a kernel

Each lesson names the kernel it needs, either **Python 3.12 (Trees from Space)** or **R 4.5 (Trees from Space)**. These kernels come from the environments described in the [environment guide](environments.md). Choose the kernel from the kernel menu in JupyterLab, or from the kernel picker in the upper right corner in VS Code. In an OnDemand session started with the Trees from Space environment, the default **Python 3** kernel is that environment. The first code cell of every lesson checks the environment and tells you if something is missing.

## Restarting

When something goes wrong, restart the kernel and run everything again:

- **JupyterLab:** *Kernel → Restart Kernel and Run All Cells*.
- **VS Code:** *Restart*, then *Run All*, in the notebook toolbar.
- **Colab:** *Runtime → Restart session and run all*.

Restarting clears the kernel's memory but keeps your edits and any files the notebook has saved. The lessons save downloaded data to a cache, so a rerun does not download it again.

## Reading an error

An error appears as a block of text called a **traceback**. Read it from the bottom up. The last line names the error type and gives a short message, such as `FileNotFoundError: ... netrc`. The lines above it show where the error occurred, ending with your cell. The lessons check for common problems, such as missing credentials or no internet connection, and print a message that says what to do next.

## Changing settings

Each lesson collects everything you might change, such as the study area, dates, and request limits, in one **settings cell** near the top. Edit values there rather than in later cells. Batch jobs read the same cell, so a batch run uses exactly the settings you saved.

## Where files go

Lessons save results to an `outputs/` folder and downloaded data to a `cache/` folder, both at the top of the repository. In Colab, these folders are inside `/content`, which disappears when the session ends, so download anything you want to keep. The [environment guide](environments.md) explains how to move these folders elsewhere.
