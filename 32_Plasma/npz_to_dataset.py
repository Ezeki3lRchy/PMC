"""
Render std2 npz files into the dataset_test_var_p_mu image format.

Per case (one .npz):
    <out>/input/<casename>/input01.png  ... input51.png    <- T_e frames
    <out>/output/<casename>/output01.png ... output51.png  <- n_e frames

Reproduces the structure that 32_Plasma/matlab_data.py used to produce via
COMSOL anim2/anim3 exports — but generated purely from the saved .npz, no
COMSOL or MATLAB launch required. Same colormap, same fixed ranges as
view_npz.py so the dataset is internally consistent.
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


def filename_to_casename(npz_path, counter):
    """Map 'material=test ..._A=0.14475_offset=...' to '0A_0.14475'."""
    stem = Path(npz_path).stem
    m = re.search(r"_A=([0-9.]+)_offset=", stem)
    if m:
        return f"{counter}A_{m.group(1)}"
    return f"{counter}A_{stem}"

# Same fixed ranges as view_npz.py — keeps the dataset comparable across cases.
NE_VMIN, NE_VMAX = 2e9, 5e15
TE_VMIN, TE_VMAX = 1.0, 10.0

# Image size — original dataset is 640x480 px.
IMG_WIDTH_IN = 6.4
IMG_HEIGHT_IN = 4.8
IMG_DPI = 100  # -> 640x480

CMAP = "plasma"


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


def _render_frame(triang, values, _grid_unused, norm, vmin, vmax, out_path):
    """Render one frame with FLAT shading (one solid color per triangle).

    tripcolor + shading='flat' assigns each triangle the mean of its 3 vertex
    values, then maps that single scalar through cmap+norm. Result:
      - smooth?  no — block-by-block, each triangle a uniform color
      - 1-1?     yes — same value always maps to same RGB
    Outside the triangulation -> no triangles -> figure facecolor (white).
    """
    fig = plt.figure(figsize=(IMG_WIDTH_IN, IMG_HEIGHT_IN), dpi=IMG_DPI,
                     facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    if norm is not None:
        ax.tripcolor(triang, values, shading="flat", cmap=CMAP, norm=norm)
    else:
        ax.tripcolor(triang, values, shading="flat", cmap=CMAP,
                     vmin=vmin, vmax=vmax)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_xlim(triang.x.min(), triang.x.max())
    ax.set_ylim(triang.y.min(), triang.y.max())
    fig.savefig(out_path, dpi=IMG_DPI, pad_inches=0, facecolor="white")
    plt.close(fig)


def render_case(npz_path, out_root, casename=None, verbose=True):
    """Render one npz to <out_root>/{input,output}/<casename>/{input,output}NN.png."""
    d, triang = _load(npz_path)
    Te = d["ptp_Te"]                  # (51, N)
    ne = d["ptp_ne"]                  # (51, N)
    n_frames = Te.shape[0]

    if casename is None:
        casename = Path(npz_path).stem

    in_dir = Path(out_root) / "input" / casename
    out_dir = Path(out_root) / "output" / casename
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    ne_norm = LogNorm(vmin=NE_VMIN, vmax=NE_VMAX)
    Te_clip = np.clip(Te, TE_VMIN, TE_VMAX)
    ne_clip = np.clip(ne, NE_VMIN, NE_VMAX)

    for i in range(n_frames):
        idx = f"{i+1:02d}"
        _render_frame(
            triang, Te_clip[i], None, None, TE_VMIN, TE_VMAX,
            in_dir / f"input{idx}.png",
        )
        _render_frame(
            triang, ne_clip[i], None, ne_norm, None, None,
            out_dir / f"output{idx}.png",
        )
    if verbose:
        print(f"  {casename:<40} {n_frames} frames -> {in_dir.parent.name}/{casename}/")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("npz", nargs="?",
                   default=r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2\argon_gec_ccp.npz",
                   help="single .npz path, OR a directory of .npz to batch")
    p.add_argument("--out", default=r"D:\32_MoviLSTM\Argon_GEC_CCP\dataset_test_var_p_mu_from_npz",
                   help="root output dir; will get input/ and output/ subdirs")
    p.add_argument("--casename", default=None,
                   help="override case folder name (single-file mode only)")
    args = p.parse_args()

    if os.path.isdir(args.npz):
        files = sorted(glob.glob(os.path.join(args.npz, "*.npz")))
    else:
        files = [args.npz]
    print(f"cases: {len(files)}  ->  {args.out}")

    for i, f in enumerate(files):
        if args.casename and len(files) == 1:
            cn = args.casename
        else:
            cn = filename_to_casename(f, i)
        print(f"[{i+1}/{len(files)}] {cn}")
        render_case(f, args.out, casename=cn)


if __name__ == "__main__":
    main()
