"""
Extract every std2 (Time Periodic to Time Dependent) field from saved .mph
files of the argon_gec_ccp sweep, one .npz per case.

Per case you get:
    coords   (2, N_nodes)        r,z node coords (axisymmetric)
    t        (51,)               time samples [0 .. 1/f0], seconds
    <field>  (51, N_nodes)       one array per FIELD expression
    g_<gx>   (51,)               one array per GLOBAL expression

Reuses the same launch chain as 32_Plasma/matlab_data.py:
    .lnk -> comsolinit.m -> comsolstartup.m (shareEngine) -> connect_matlab.

Run on one file: set CASES_DIR = None and INPUT_MPH_PATH = '<file>.mph'.
Run on the whole sweep: set CASES_DIR = 'D:/.../cas'.
"""

import glob
import os
import sys
import time
import traceback
from pathlib import Path

import matlab.engine
import numpy as np

# ---- bridge config (same as 32_Plasma/matlab_data.py) ----
SHORTCUT_PATH = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\COMSOL Multiphysics 6.3"
SHORTCUT_NAME = "COMSOL Multiphysics 6.3 with MATLAB.lnk"
FULL_PATH = os.path.join(SHORTCUT_PATH, SHORTCUT_NAME)

# ---- inputs / outputs ----
# Single-file mode:
INPUT_MPH_PATH = os.path.normpath(r"D:\32_MoviLSTM\Argon_GEC_CCP\argon_gec_ccp.mph")
# Batch mode (set to None to disable). Globs every .mph under here.
CASES_DIR = os.path.normpath(r"D:\32_MoviLSTM\Argon_GEC_CCP\cas")
OUT_DIR = os.path.normpath(r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2")

# ---- what to pull from std2 ----
# Plasma, Time Periodic (ptp) standard variables for the GEC CCP model.
# All evaluated on the std2 dataset, so each becomes a (51, N_nodes) array.
# If a variable does not exist for this .mph it is skipped, not fatal.
FIELD_EXPRS = [
    "V",                  # electric potential
    "ptp.ne",             # electron density
    "ptp.Te",             # electron temperature
    "ptp.nepsilon",       # electron energy density (a.k.a. n_eps)
    "ptp.Re",             # ionization rate (instantaneous)
    "ptp.Pelec",          # power deposition to electrons (W/m^3)
    "ptp.Er",             # E-field, r-component
    "ptp.Ez",             # E-field, z-component
    "ptp.Jr",             # current density, r
    "ptp.Jz",             # current density, z
]

GLOBAL_EXPRS = [
    "ptp.mct1.Va_per",    # voltage amplitude (V)
    "ptp.mct1.Vdcb_per",  # DC self-bias (V)
]

# Dataset tag std2 stores its solution under. COMSOL auto-creates dset2
# for the second study; if discovery says otherwise we fall back automatically.
STD2_DATASET_DEFAULT = "dset2"


# ---------------- engine bring-up ----------------

def matlab_init(i_path=FULL_PATH):
    os.startfile(i_path)
    time.sleep(5)
    for attempt in range(21):
        sessions = matlab.engine.find_matlab()
        if sessions:
            eng = matlab.engine.connect_matlab(sessions[0])
            eng.eval("disp('connected')", nargout=0)
            return eng
        time.sleep(3)
    raise RuntimeError("Failed to connect to MATLAB session after retries.")


# ---------------- per-.mph helpers ----------------

def find_std2_dataset(eng, tag="model"):
    """Return the dataset tag whose solution comes from std2.

    Strategy: list dataset tags via mphtags, ask each for its solution tag,
    pick the one tied to std2/sol2. Falls back to STD2_DATASET_DEFAULT.
    """
    try:
        eng.eval(f"ds_tags = mphtags({tag}.result.dataset);", nargout=0)
        n = int(eng.eval("numel(ds_tags)", nargout=1))
        for i in range(1, n + 1):
            try:
                # Solution tag attached to dataset i
                sol_tag = eng.eval(
                    f"char({tag}.result.dataset(ds_tags{{{i}}}).getString('solution'))",
                    nargout=1,
                )
                ds_tag = eng.eval(f"char(ds_tags{{{i}}})", nargout=1)
                if isinstance(sol_tag, str) and "sol2" in sol_tag:
                    return ds_tag
            except matlab.engine.MatlabExecutionError:
                continue
    except matlab.engine.MatlabExecutionError:
        pass
    return STD2_DATASET_DEFAULT


def eval_field_on_dataset(eng, expr, dataset, tag="model"):
    """mpheval(expr, 'dataset', dataset) -> (coords, triangulation, values).

    Note: mpheval's `d.t` is the MESH TRIANGULATION (int32, 3 x n_tri or
    4 x n_tri), NOT time. Pull the time vector separately via
    get_time_array().
    """
    eng.eval(
        f"d = mpheval({tag}, '{expr}', 'dataset', '{dataset}');", nargout=0,
    )
    coords = np.asarray(eng.eval("d.p", nargout=1))
    values = np.asarray(eng.eval("d.d1", nargout=1))
    tri = np.asarray(eng.eval("d.t", nargout=1)).astype(np.int32)
    return coords, values, tri


def eval_global_on_dataset(eng, expr, dataset, tag="model"):
    eng.eval(
        f"g = mphglobal({tag}, '{expr}', 'dataset', '{dataset}');", nargout=0,
    )
    return np.asarray(eng.eval("g", nargout=1)).ravel()


def get_time_array(eng, dataset, tag="model"):
    """Pull the time vector for a time-dependent dataset.

    Resolves the soltag via dataset.getString('solution') -> mphsolinfo.
    Returns an empty array if the solution is not time-dep (e.g., std1).
    """
    try:
        eng.eval(
            f"sol_tag = char({tag}.result.dataset('{dataset}').getString('solution'));",
            nargout=0,
        )
        eng.eval(f"info = mphsolinfo({tag}, 'soltag', sol_tag);", nargout=0)
        return np.asarray(eng.eval("info.solvals", nargout=1)).ravel()
    except matlab.engine.MatlabExecutionError:
        return np.array([])


def discover_variables(eng, dataset, tag="model", prefix="ptp."):
    """List variables defined on the geometry that match a name prefix.

    Useful first time on a new .mph to find correct variable names.
    Calls mphxmeshstats / mphfield to enumerate. Returns a list of names.
    """
    try:
        eng.eval(f"info = mphxmeshinfo({tag});", nargout=0)
        names = eng.eval("info.fieldnames", nargout=1)
        out = [str(n) for n in (names if isinstance(names, list) else [names])]
        if prefix:
            out = [n for n in out if n.startswith(prefix)]
        return sorted(out)
    except matlab.engine.MatlabExecutionError:
        return []


def safe_key(expr):
    return (
        expr.replace(".", "_")
        .replace("(", "_").replace(")", "")
        .replace(" ", "")
    )


def extract_one(eng, mph_path, out_path):
    """Load one .mph, dump everything for std2 to a single .npz."""
    eng.eval(f"model = mphload('{mph_path.replace(chr(92), chr(92)*2)}');", nargout=0)
    dset = find_std2_dataset(eng)
    print(f"  std2 dataset = {dset}")

    # Time vector (pulled once from solution metadata, not from mpheval).
    times = get_time_array(eng, dset)
    print(f"  time array  -> {times.shape} ({times[0]:.3e} .. {times[-1]:.3e} s)" if times.size else "  time array  -> (none)")

    bundle = {
        "_dataset": np.array(dset),
        "_source_mph": np.array(mph_path),
        "t": times,
    }
    coords_saved = False
    tri_saved = False

    for expr in FIELD_EXPRS:
        try:
            coords, values, tri = eval_field_on_dataset(eng, expr, dset)
        except matlab.engine.MatlabExecutionError as e:
            print(f"  {expr:<18} SKIP ({str(e).splitlines()[0][:80]})")
            continue
        if not coords_saved:
            bundle["coords"] = coords            # (dim, N)
            coords_saved = True
        if not tri_saved:
            bundle["triangulation"] = tri        # (4, n_tri) — for plotting
            tri_saved = True
        bundle[safe_key(expr)] = values          # (T, N)
        print(f"  {expr:<18} -> {values.shape}")

    for expr in GLOBAL_EXPRS:
        try:
            arr = eval_global_on_dataset(eng, expr, dset)
            bundle[f"g_{safe_key(expr)}"] = arr
            print(f"  {expr:<22} -> {arr.shape} (global)")
        except matlab.engine.MatlabExecutionError as e:
            print(f"  {expr:<22} SKIP ({str(e).splitlines()[0][:80]})")

    np.savez_compressed(out_path, **bundle)
    # free MATLAB workspace before next case
    eng.eval("clear model d g info sol_tag", nargout=0)
    return out_path


# ---------------- main / batch ----------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # also render PNG dataset alongside extraction (rendering is cheap;
    # done inline so it overlaps with COMSOL working on the next case)
    DATASET_OUT = os.path.normpath(
        r"D:\32_MoviLSTM\Argon_GEC_CCP\dataset_test_var_p_mu_from_npz"
    )
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from npz_to_dataset import render_case, filename_to_casename
        do_render = True
    except Exception as e:
        print(f"WARN: cannot import npz_to_dataset ({e}); skipping PNG render")
        do_render = False

    if CASES_DIR and os.path.isdir(CASES_DIR):
        mphs = sorted(glob.glob(os.path.join(CASES_DIR, "*.mph")))
    else:
        mphs = [INPUT_MPH_PATH]
    print(f"cases to process: {len(mphs)}")

    eng = matlab_init()
    failed = []
    try:
        for i, mph in enumerate(mphs):
            stem = Path(mph).stem
            out = os.path.join(OUT_DIR, stem + ".npz")
            casename = filename_to_casename(out, i) if do_render else None

            extracted_now = False
            if os.path.exists(out):
                print(f"[{i+1}/{len(mphs)}] npz exists, skip extract: {stem}")
            else:
                print(f"[{i+1}/{len(mphs)}] extracting: {stem}")
                try:
                    extract_one(eng, mph, out)
                    extracted_now = True
                except Exception:
                    traceback.print_exc()
                    failed.append(mph)
                    continue

            # render PNGs from npz (always; idempotent)
            if do_render:
                try:
                    print(f"  -> rendering PNGs as case '{casename}'")
                    render_case(out, DATASET_OUT, casename=casename, verbose=False)
                except Exception:
                    print("  render failed:")
                    traceback.print_exc()

            # bounce engine every 50 EXTRACTIONS (skips don't count)
            if extracted_now and (i + 1) % 50 == 0:
                print(f"-- restarting engine after {i+1} cases --")
                try:
                    eng.exit()
                except Exception:
                    pass
                import subprocess
                for proc in ("MATLAB.exe", "comsolmphserver.exe"):
                    subprocess.run(["taskkill", "/F", "/IM", proc])
                eng = matlab_init()
    finally:
        if failed:
            print("FAILED cases:")
            for f in failed:
                print("  ", f)


if __name__ == "__main__":
    main()
