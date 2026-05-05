"""
Render std2 npz files into a UNIFORM 60x80 sample grid, output as 640x480 PNG.

Key difference from npz_to_dataset.py:
  - That one rendered the FEM triangulation directly (block density follows
    mesh — dense near sheath, sparse in bulk).
  - This one resamples onto a uniform 60x80 grid (cells are 1.69 mm tall x
    1.27 mm wide). Each cell -> one solid color block in the PNG.
    Sheath detail is lost; bulk is preserved at its natural resolution.

Per-cell value comes from LinearTriInterpolator at the cell center
(no smoothing across cells — imshow uses interpolation='nearest').
Cells whose center falls outside the triangulation (inside the metal
electrodes) -> NaN -> rendered as the white figure background.
"""

import argparse
import glob
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.tri import LinearTriInterpolator

# Color ranges — same as flat-shading dataset for cross-comparability.
NE_VMIN, NE_VMAX = 2e9, 5e15
TE_VMIN, TE_VMAX = 1.0, 10.0

# PNG canvas (kept identical to the FEM dataset PNGs).
IMG_WIDTH_IN = 6.4
IMG_HEIGHT_IN = 4.8
IMG_DPI = 100  # -> 640x480 px

# Uniform value grid resolution.
GRID_H = 60
GRID_W = 80

CMAP = "plasma"


def filename_to_casename(npz_path, counter):
    stem = Path(npz_path).stem
    m = re.search(r"_A=([0-9.]+)_offset=", stem)
    if m:
        return f"{counter}A_{m.group(1)}"
    return f"{counter}A_{stem}"


def _load(npz_path):
    d = np.load(npz_path, allow_pickle=True)
    coords = d["coords"]
    r, z = coords[0], coords[1]
    tri_raw = d["triangulation"]
    tri = (tri_raw[:3].T if tri_raw.shape[0] in (3, 4) else tri_raw[:, :3])
    if tri.min() == 1:
        tri = tri - 1
    triang = mtri.Triangulation(r, z, tri)
    return d, triang


def _make_uniform_grid(triang, grid_h=GRID_H, grid_w=GRID_W):
    """Cell-center grid covering the triangulation's bounding box."""
    xmin, xmax = float(triang.x.min()), float(triang.x.max())
    ymin, ymax = float(triang.y.min()), float(triang.y.max())
    dx = (xmax - xmin) / grid_w
    dy = (ymax - ymin) / grid_h
    xs = np.linspace(xmin + dx / 2, xmax - dx / 2, grid_w)
    ys = np.linspace(ymin + dy / 2, ymax - dy / 2, grid_h)
    return np.meshgrid(xs, ys), (xmin, xmax, ymin, ymax)


def _render_frame(triang, values, grid, extent, norm, vmin, vmax, out_path):
    """Sample on uniform grid (cell centers), render as solid blocks."""
    XG, YG = grid
    interp = LinearTriInterpolator(triang, values)
    Z = interp(XG, YG)  # masked array — NaN outside geometry

    fig = plt.figure(figsize=(IMG_WIDTH_IN, IMG_HEIGHT_IN), dpi=IMG_DPI,
                     facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    if norm is not None:
        ax.imshow(Z, origin="lower", cmap=CMAP, norm=norm,
                  extent=extent, interpolation="nearest", aspect="equal")
    else:
        ax.imshow(Z, origin="lower", cmap=CMAP, vmin=vmin, vmax=vmax,
                  extent=extent, interpolation="nearest", aspect="equal")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
    fig.savefig(out_path, dpi=IMG_DPI, pad_inches=0, facecolor="white")
    plt.close(fig)


def render_case(npz_path, out_root, casename=None, verbose=True):
    d, triang = _load(npz_path)
    Te = d["ptp_Te"]
    ne = d["ptp_ne"]
    n_frames = Te.shape[0]

    if casename is None:
        casename = Path(npz_path).stem

    in_dir = Path(out_root) / "input" / casename
    out_dir = Path(out_root) / "output" / casename
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Per-case grid (same for all 51 frames within a case).
    grid, extent = _make_uniform_grid(triang)
    ne_norm = LogNorm(vmin=NE_VMIN, vmax=NE_VMAX)
    Te_clip = np.clip(Te, TE_VMIN, TE_VMAX)
    ne_clip = np.clip(ne, NE_VMIN, NE_VMAX)

    for i in range(n_frames):
        idx = f"{i+1:02d}"
        _render_frame(triang, Te_clip[i], grid, extent, None,
                      TE_VMIN, TE_VMAX, in_dir / f"input{idx}.png")
        _render_frame(triang, ne_clip[i], grid, extent, ne_norm,
                      None, None, out_dir / f"output{idx}.png")
    if verbose:
        print(f"  {casename:<40} {n_frames} frames @ {GRID_H}x{GRID_W}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("npz", nargs="?",
                   default=r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2\argon_gec_ccp.npz")
    p.add_argument("--out",
                   default=r"D:\32_MoviLSTM\Argon_GEC_CCP\dataset_test_var_p_mu_from_npz_60x80")
    p.add_argument("--casename", default=None)
    args = p.parse_args()

    if os.path.isdir(args.npz):
        files = sorted(glob.glob(os.path.join(args.npz, "*.npz")))
    else:
        files = [args.npz]
    print(f"cases: {len(files)}  ->  {args.out}  (grid {GRID_H}x{GRID_W})")
    for i, f in enumerate(files):
        cn = args.casename if (args.casename and len(files) == 1) else filename_to_casename(f, i)
        print(f"[{i+1}/{len(files)}] {cn}")
        render_case(f, args.out, casename=cn)


if __name__ == "__main__":
    main()
