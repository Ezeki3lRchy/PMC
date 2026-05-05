"""Quick inspector for one std2 .npz produced by extract_std2.py.

Prints summary, then renders 2 figures:
  fig 1: ne and Te snapshots at frames 0, 12, 25, 37, 50  (10 panels)
  fig 2: time series at the gap centerline node closest to (r=0, z=L/2)

PNGs land next to the .npz with the same stem.
"""

import os
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")  # no GUI needed
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import LogNorm

# Fixed colorbar ranges for cross-case comparability.
# n_e spans 6 orders of magnitude -> log scale.
NE_VMIN, NE_VMAX = 2e9, 5e15
TE_VMIN, TE_VMAX = 1.0, 10.0

# Sheath zoom window — z range to zoom into for the high-gradient region.
# The driven electrode sits at z=0; sheath extends ~3 mm into the gap.
SHEATH_ZOOM_Z = (-0.001, 0.005)   # 6 mm tall window straddling the electrode
SHEATH_ZOOM_R = (0.0, 0.054)      # only over the powered electrode radius


def main(npz_path):
    d = np.load(npz_path, allow_pickle=True)
    print(f"=== {npz_path}")
    print("keys + shapes:")
    for k in sorted(d.files):
        a = d[k]
        s = f"  {k:<22} {a.shape}  {a.dtype}"
        if a.ndim == 0:
            s += f"  = {a}"
        elif a.ndim == 1:
            s += f"  range [{a.min():.3e}, {a.max():.3e}]"
        else:
            s += f"  range [{a.min():.3e}, {a.max():.3e}]"
        print(s)

    coords = d["coords"]            # (2, N)
    r, z = coords[0], coords[1]
    t = d["t"]                       # (51,)
    ne = d["ptp_ne"]                 # (51, N)
    Te = d["ptp_Te"]                 # (51, N)

    # Build the matplotlib triangulation. Auto-detect 0- vs 1-based indexing.
    tri_raw = d["triangulation"]
    if tri_raw.shape[0] in (3, 4):
        tri = tri_raw[:3].T          # (n_tri, 3)
    else:
        tri = tri_raw[:, :3]
    if tri.min() == 1:
        tri = tri - 1
    triang = mtri.Triangulation(r, z, tri)

    stem = os.path.splitext(npz_path)[0]
    frames = [0, 12, 25, 37, 50]

    # ---- figure 1: spatial snapshots at 5 phases ----
    # plasma colormap, FIXED colorbar range across all frames AND across
    # cases (constants at top of file) so plots from different sweep cases
    # can be visually compared. n_e on log scale because dynamic range is
    # 6 decades; T_e linear.
    cmap = "plasma"
    ne_norm = LogNorm(vmin=NE_VMIN, vmax=NE_VMAX)
    ne_levels = np.logspace(np.log10(NE_VMIN), np.log10(NE_VMAX), 21)
    Te_levels = np.linspace(TE_VMIN, TE_VMAX, 21)
    # clip so out-of-range values don't blow up LogNorm
    ne_clip = np.clip(ne, NE_VMIN, NE_VMAX)
    Te_clip = np.clip(Te, TE_VMIN, TE_VMAX)

    fig, axes = plt.subplots(2, 5, figsize=(20, 7), constrained_layout=True)
    for j, fi in enumerate(frames):
        cs0 = axes[0, j].tricontourf(
            triang, ne_clip[fi], levels=ne_levels, cmap=cmap,
            norm=ne_norm, extend="both",
        )
        axes[0, j].set_title(f"n_e   t = {t[fi]*1e9:.1f} ns")
        axes[0, j].set_aspect("equal")
        axes[0, j].set_xlabel("r (m)")

        cs1 = axes[1, j].tricontourf(
            triang, Te_clip[fi], levels=Te_levels, cmap=cmap,
            vmin=TE_VMIN, vmax=TE_VMAX, extend="both",
        )
        axes[1, j].set_title(f"T_e   t = {t[fi]*1e9:.1f} ns")
        axes[1, j].set_aspect("equal")
        axes[1, j].set_xlabel("r (m)")

    axes[0, 0].set_ylabel("z (m)")
    axes[1, 0].set_ylabel("z (m)")

    # one shared colorbar per row
    fig.colorbar(cs0, ax=axes[0, :], shrink=0.85,
                 label=f"n_e (1/m^3)  log[{NE_VMIN:.0e}, {NE_VMAX:.0e}]")
    fig.colorbar(cs1, ax=axes[1, :], shrink=0.85,
                 label=f"T_e  [{TE_VMIN}, {TE_VMAX}]")

    fig.suptitle(
        f"{os.path.basename(npz_path)} — snapshots (fixed range, plasma cmap)",
        fontsize=14,
    )
    out1 = stem + "_snapshots.png"
    fig.savefig(out1, dpi=120)
    print(f"\nsaved -> {out1}")

    # ---- figure 1b: same data, zoomed onto the sheath / driven-electrode ----
    fig, axes = plt.subplots(2, 5, figsize=(20, 6), constrained_layout=True)
    for j, fi in enumerate(frames):
        cs0 = axes[0, j].tricontourf(
            triang, ne_clip[fi], levels=ne_levels, cmap=cmap,
            norm=ne_norm, extend="both",
        )
        axes[0, j].set_xlim(*SHEATH_ZOOM_R)
        axes[0, j].set_ylim(*SHEATH_ZOOM_Z)
        axes[0, j].set_title(f"n_e   t = {t[fi]*1e9:.1f} ns")
        axes[0, j].set_aspect("auto")  # exaggerate z to show structure

        cs1 = axes[1, j].tricontourf(
            triang, Te_clip[fi], levels=Te_levels, cmap=cmap,
            vmin=TE_VMIN, vmax=TE_VMAX, extend="both",
        )
        axes[1, j].set_xlim(*SHEATH_ZOOM_R)
        axes[1, j].set_ylim(*SHEATH_ZOOM_Z)
        axes[1, j].set_title(f"T_e   t = {t[fi]*1e9:.1f} ns")
        axes[1, j].set_aspect("auto")

        # overlay the actual mesh nodes so you can SEE the resolution
        in_window = (
            (r >= SHEATH_ZOOM_R[0]) & (r <= SHEATH_ZOOM_R[1]) &
            (z >= SHEATH_ZOOM_Z[0]) & (z <= SHEATH_ZOOM_Z[1])
        )
        for ax in (axes[0, j], axes[1, j]):
            ax.plot(r[in_window], z[in_window], ".",
                    ms=1.0, color="white", alpha=0.4)

    axes[0, 0].set_ylabel("z (m)")
    axes[1, 0].set_ylabel("z (m)")
    fig.colorbar(cs0, ax=axes[0, :], shrink=0.85,
                 label=f"n_e (1/m^3)  log[{NE_VMIN:.0e}, {NE_VMAX:.0e}]")
    fig.colorbar(cs1, ax=axes[1, :], shrink=0.85,
                 label=f"T_e  [{TE_VMIN}, {TE_VMAX}]")
    fig.suptitle(
        f"{os.path.basename(npz_path)} — sheath zoom (z ∈ {SHEATH_ZOOM_Z} m, white dots = mesh nodes)",
        fontsize=13,
    )
    out1z = stem + "_sheath.png"
    fig.savefig(out1z, dpi=120)
    print(f"saved -> {out1z}")

    # ---- figure 2: time series at gap-center, on axis (r ~ 0, z ~ midgap) ----
    L = z.max() - z.min()
    z_mid = z.min() + 0.5 * L
    score = np.hypot(r, z - z_mid)
    k = int(np.argmin(score))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    axes[0].plot(t * 1e9, ne[:, k], lw=1.5)
    axes[0].set_xlabel("t (ns)")
    axes[0].set_ylabel("n_e (1/m^3)")
    axes[0].set_title(f"n_e at node {k}  (r={r[k]:.4f}, z={z[k]:.4f})")
    axes[0].grid(True)
    axes[1].plot(t * 1e9, Te[:, k], lw=1.5, color="C1")
    axes[1].set_xlabel("t (ns)")
    axes[1].set_ylabel("T_e")
    axes[1].set_title(f"T_e at node {k}")
    axes[1].grid(True)
    out2 = stem + "_timeseries.png"
    fig.savefig(out2, dpi=120)
    print(f"saved -> {out2}")


if __name__ == "__main__":
    npz = sys.argv[1] if len(sys.argv) > 1 else r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2\argon_gec_ccp.npz"
    main(npz)
