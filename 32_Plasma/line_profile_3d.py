"""3D surface plot of T_e and n_e along two cut lines vs time.

Two lines:
  vertical   : r = 0.025 m,  z from 0 to L (gap height)
  horizontal : z = 0.001 m,  r from 0 to R2 (across the discharge)

Output: 4 separate PNGs, each with a small geometry thumbnail showing
the cut line used.
"""

import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import matplotlib.tri as mtri    # noqa: E402
from matplotlib.tri import LinearTriInterpolator  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401, E402


def log10_formatter(x, pos):
    """Format a log10-space value `x` as 10^x in math text."""
    return rf"$10^{{{int(round(x))}}}$"

# GEC reactor dimensions (m)
GEOM_R1 = 0.0538
GEOM_R2 = 0.1016
GEOM_L = 0.0254
GEOM_HD = 0.1016
CHAM_Z_LO = -GEOM_HD / 2 + GEOM_L / 2   # -0.0381
CHAM_Z_HI = GEOM_HD / 2 + GEOM_L / 2    # +0.0635


def draw_geometry_inset(fig, rect, line_pts):
    """Draw reactor outline + the cut line as a small inset on `fig`.

    rect      : (x, y, w, h) in figure-fraction coordinates.
    line_pts  : ((r0, z0), (r1, z1)) endpoints in metres.
    """
    ax = fig.add_axes(rect)
    # gap rectangle [0, R1] x [0, L]
    ax.add_patch(mpatches.Rectangle((0, 0), GEOM_R1, GEOM_L,
                                    facecolor="#dddddd",
                                    edgecolor="black", lw=0.8))
    # chamber rectangle [R1, R2] x [Cham_lo, Cham_hi]
    ax.add_patch(mpatches.Rectangle(
        (GEOM_R1, CHAM_Z_LO), GEOM_R2 - GEOM_R1, CHAM_Z_HI - CHAM_Z_LO,
        facecolor="#dddddd", edgecolor="black", lw=0.8,
    ))
    # the cut line
    (r0, z0), (r1, z1) = line_pts
    ax.plot([r0, r1], [z0, z1], color="red", lw=2.0)
    ax.annotate(
        "", xy=(r1, z1), xytext=(r0, z0),
        arrowprops=dict(arrowstyle="->", color="red", lw=1.8),
    )
    ax.set_xlim(-0.005, GEOM_R2 + 0.005)
    ax.set_ylim(CHAM_Z_LO - 0.005, CHAM_Z_HI + 0.005)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_facecolor("white")
    ax.set_title("cut line", fontsize=8, pad=2)
    ax.set_zorder(10)  # keep inset above any 3D-plot bleed


def sample_line_over_time(triang, field_TxN, r_line, z_line):
    """field_TxN shape (T, N) -> returns (T, M) sampled along the line."""
    out = np.full((field_TxN.shape[0], len(r_line)), np.nan)
    for i in range(field_TxN.shape[0]):
        interp = LinearTriInterpolator(triang, field_TxN[i])
        masked = interp(r_line, z_line)
        out[i] = masked.filled(np.nan)
    return out


def main(npz_path, out_png):
    d = np.load(npz_path, allow_pickle=True)
    r, z = d["coords"]
    tri = d["triangulation"][:3].T
    if tri.min() == 1:
        tri = tri - 1
    triang = mtri.Triangulation(r, z, tri)

    t = d["t"]                                                  # (51,)
    Te = d["ptp_Te"]                                            # (51, N)
    ne = d["ptp_ne"]                                            # (51, N)

    # vertical line through the gap (r=25mm, z=0..L)
    n_v = 120
    r_v = np.full(n_v, 0.025)
    z_v = np.linspace(0.0002, 0.0252, n_v)

    # horizontal line just above the powered electrode (z=1mm, r=0..R2)
    n_h = 200
    r_h = np.linspace(0.001, 0.100, n_h)
    z_h = np.full(n_h, 0.001)

    Te_v = sample_line_over_time(triang, Te, r_v, z_v)
    ne_v = sample_line_over_time(triang, ne, r_v, z_v)
    Te_h = sample_line_over_time(triang, Te, r_h, z_h)
    ne_h = sample_line_over_time(triang, ne, r_h, z_h)

    print(f"vertical   sampled: Te {Te_v.shape}, ne {ne_v.shape}, "
          f"Te valid {(~np.isnan(Te_v)).sum()/Te_v.size*100:.0f}%")
    print(f"horizontal sampled: Te {Te_h.shape}, ne {ne_h.shape}, "
          f"Te valid {(~np.isnan(Te_h)).sum()/Te_h.size*100:.0f}%")

    t_ns = t * 1e9                  # ns
    z_v_mm = z_v * 1000             # mm
    r_h_mm = r_h * 1000             # mm

    out_dir = os.path.dirname(out_png)
    stem = os.path.splitext(os.path.basename(out_png))[0]

    line_v = ((0.025, z_v[0]), (0.025, z_v[-1]))
    line_h = ((r_h[0], 0.001), (r_h[-1], 0.001))

    NE_LBL = r"$n_e\ (\mathrm{m}^{-3})$"
    TE_LBL = r"$T_e\ (\mathrm{eV})$"
    Z_LBL = r"$z\ (\mathrm{mm})$"
    R_LBL = r"$r\ (\mathrm{mm})$"
    T_LBL = r"$t\ (\mathrm{ns})$"

    # Apply log10 to n_e (3D matplotlib can't reliably set_zscale('log'))
    eps = 1e-3   # avoid log(0)
    ne_v_log = np.log10(np.where(ne_v > eps, ne_v, eps))
    ne_h_log = np.log10(np.where(ne_h > eps, ne_h, eps))

    panels = [
        (Te_v, z_v_mm, Z_LBL, TE_LBL,
         r"$T_e$ along vertical line at $r=25$ mm",
         "Te_vertical_r25mm", line_v, False),
        (Te_h, r_h_mm, R_LBL, TE_LBL,
         r"$T_e$ along horizontal line at $z=1$ mm",
         "Te_horizontal_z1mm", line_h, False),
        (ne_v_log, z_v_mm, Z_LBL, NE_LBL,
         r"$n_e$ along vertical line at $r=25$ mm  (log scale)",
         "ne_vertical_r25mm", line_v, True),
        (ne_h_log, r_h_mm, R_LBL, NE_LBL,
         r"$n_e$ along horizontal line at $z=1$ mm  (log scale)",
         "ne_horizontal_z1mm", line_h, True),
    ]
    for arr, axis, xlab, zlab, title, key, line, is_log in panels:
        fig = plt.figure(figsize=(9, 7))
        ax = fig.add_subplot(111, projection="3d")
        S, T = np.meshgrid(axis, t_ns)
        Z = np.where(np.isnan(arr), 0, arr)
        surf = ax.plot_surface(
            S, T, Z, cmap="plasma", edgecolor="none",
            rcount=51, ccount=120, antialiased=True,
        )
        ax.set_xlabel(xlab, labelpad=8)
        ax.set_ylabel(T_LBL, labelpad=8)
        ax.set_zlabel(zlab, labelpad=10)
        ax.set_title(title, fontsize=13)
        ax.view_init(elev=25, azim=-60)

        if is_log:
            # axis ticks at integer log decades, formatted as 10^x
            zmin, zmax = int(np.floor(np.nanmin(arr))), int(np.ceil(np.nanmax(arr)))
            ticks = np.arange(zmin, zmax + 1)
            ax.set_zticks(ticks)
            ax.zaxis.set_major_formatter(mticker.FuncFormatter(log10_formatter))

        cb = fig.colorbar(surf, ax=ax, shrink=0.55, pad=0.10, location="right")
        cb.set_label(zlab)
        if is_log:
            cb.set_ticks(np.arange(int(np.floor(np.nanmin(arr))),
                                   int(np.ceil(np.nanmax(arr))) + 1))
            cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(log10_formatter))

        draw_geometry_inset(fig, rect=(0.01, 0.74, 0.18, 0.22),
                            line_pts=line)

        path = os.path.join(out_dir, f"{stem}_{key}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"saved -> {path}")


if __name__ == "__main__":
    npz = (sys.argv[1] if len(sys.argv) > 1 else
           r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2\argon_gec_ccp.npz")
    out = (sys.argv[2] if len(sys.argv) > 2 else
           r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2\argon_gec_ccp_lineprofile3d.png")
    main(npz, out)
