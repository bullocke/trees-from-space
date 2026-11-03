"""Repository rules that a reviewer should not have to check by eye.

1. No tracked file holds a personal path, a uNID, a CHPC account name, or a
   token-like string. The patterns here are generic. Real names belong in
   ``~/.config/trees-from-space/private-patterns.txt`` (one regular expression
   per line), which this test reads when it exists and which never enters the
   repository. Placeholders such as ``<uNID>`` and ``$USER`` are allowed.
2. No code or notebook disables TLS verification (``GDAL_HTTP_UNSAFESSL``).
3. Notebooks are committed without outputs; expected results are PNG files.
4. Every lesson and template notebook has exactly one cell tagged
   ``parameters``, the cell papermill replaces in batch runs.
5. Site coordinates written inline in a notebook match
   ``examples/sites.geojson``, so a notebook opened alone (for example in
   Colab) uses the same study area as the rest of the repository.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PRIVATE_PATTERNS = Path.home() / ".config" / "trees-from-space" / "private-patterns.txt"
SITES = REPO / "examples" / "sites.geojson"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".tif", ".tiff"}
CODE_SUFFIXES = {".py", ".r", ".sh", ".sbatch", ".yml", ".yaml", ".ipynb"}

GENERIC_PATTERNS = (
    r"\bu\d{7}\b",  # University of Utah uNID
    r"/uufs/(?!chpc\.utah\.edu/common/home/<)",  # CHPC paths, unless a placeholder
    r"/home/[a-z][a-z0-9_-]+/",  # a local home directory
    r"/mnt/c/Users/",  # a Windows home seen from WSL
    r"/Users/[A-Za-z][A-Za-z0-9_-]+/",  # a macOS home directory
    # An account on a command line or an #SBATCH line. Placeholders (<...>,
    # $VAR, EDIT) and the public data transfer account are allowed.
    r"--account[= ](?!<|\$|EDIT\b|dtn\b)[A-Za-z0-9]",
    r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}",  # a JSON Web Token
)
UNSAFE_SSL = re.compile(
    r"GDAL_HTTP_UNSAFESSL[\"'\s]*[,=:)]\s*[\"']?(YES|TRUE|ON|1)", re.I
)


def _tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    this_file = Path(__file__).resolve()
    files = []
    for name in out.stdout.splitlines():
        path = REPO / name
        if path.suffix.lower() in BINARY_SUFFIXES or path.resolve() == this_file:
            continue
        if path.is_file():
            files.append(path)
    return files


def _notebooks() -> list[Path]:
    found = []
    for folder in ("tutorials", "templates"):
        found += [
            p
            for p in (REPO / folder).rglob("*.ipynb")
            if ".ipynb_checkpoints" not in p.parts
        ]
    return sorted(found)


def _patterns() -> list[re.Pattern[str]]:
    patterns = list(GENERIC_PATTERNS)
    if PRIVATE_PATTERNS.exists():
        patterns += [
            line.strip()
            for line in PRIVATE_PATTERNS.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    return [re.compile(p) for p in patterns]


def _cell_source(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


def test_no_tracked_file_holds_private_names_paths_or_tokens():
    patterns = _patterns()
    hits = []
    for path in _tracked_files():
        text = path.read_text(errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{path.relative_to(REPO)}:{line}: {match.group(0)!r}")
    assert not hits, "Private names, paths, or tokens in tracked files:\n" + "\n".join(
        hits
    )


def test_no_code_disables_tls_verification():
    hits = []
    for path in _tracked_files():
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        text = path.read_text(errors="ignore")
        if path.suffix.lower() == ".ipynb":
            cells = json.loads(text).get("cells", [])
            text = "\n".join(_cell_source(c) for c in cells if c["cell_type"] == "code")
        if UNSAFE_SSL.search(text):
            hits.append(str(path.relative_to(REPO)))
    assert not hits, "GDAL_HTTP_UNSAFESSL enabled in: " + ", ".join(hits)


@pytest.mark.parametrize("path", _notebooks(), ids=lambda p: p.name)
def test_notebook_has_no_outputs(path):
    cells = json.loads(path.read_text())["cells"]
    dirty = [
        i
        for i, c in enumerate(cells)
        if c["cell_type"] == "code" and (c.get("outputs") or c.get("execution_count"))
    ]
    assert not dirty, f"{path.name}: outputs in cells {dirty}; run nbstripout"


@pytest.mark.parametrize("path", _notebooks(), ids=lambda p: p.name)
def test_notebook_has_one_parameters_cell(path):
    cells = json.loads(path.read_text())["cells"]
    tagged = [
        i
        for i, c in enumerate(cells)
        if "parameters" in c.get("metadata", {}).get("tags", [])
    ]
    assert len(tagged) == 1, f"{path.name}: cells tagged 'parameters': {tagged}"


SITE_ID_RE = re.compile(r"^SITE_ID\s*(?:=|<-)\s*[\"']([\w-]+)[\"']", re.M)
BBOX_RE = re.compile(r"^BBOX\s*(?:=|<-)\s*(?:c)?\(([^)]*)\)", re.M)


def _site_bounds() -> dict[str, tuple[float, ...]]:
    features = json.loads(SITES.read_text())["features"]
    bounds = {}
    for feature in features:
        ring = feature["geometry"]["coordinates"][0]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        bounds[feature["properties"]["site_id"]] = (min(xs), min(ys), max(xs), max(ys))
    return bounds


@pytest.mark.parametrize("path", _notebooks(), ids=lambda p: p.name)
def test_inline_site_matches_sites_geojson(path):
    if not SITES.exists():
        pytest.skip("examples/sites.geojson not written yet")
    cells = json.loads(path.read_text())["cells"]
    source = "\n".join(_cell_source(c) for c in cells if c["cell_type"] == "code")
    site = SITE_ID_RE.search(source)
    bbox = BBOX_RE.search(source)
    if not (site and bbox):
        pytest.skip(f"{path.name} defines no SITE_ID/BBOX")
    sites = _site_bounds()
    assert site.group(1) in sites, f"{path.name}: unknown site {site.group(1)!r}"
    inline = tuple(float(v) for v in bbox.group(1).split(","))
    assert inline == pytest.approx(sites[site.group(1)], abs=1e-9), (
        f"{path.name}: BBOX {inline} differs from sites.geojson "
        f"{sites[site.group(1)]}"
    )
