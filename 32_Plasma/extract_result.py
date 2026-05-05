"""
Extract numeric result values from a saved COMSOL .mph via LiveLink for MATLAB.

Bridge sequence is the same as matlab_data.py:
  Python -> os.startfile('COMSOL ... with MATLAB.lnk') -> comsolinit.m
        -> comsolstartup.m (cd + matlab.engine.shareEngine) -> connect_matlab.

What is different from matlab_data.py:
  no parameter sweep, no image export. We mphload the model once and pull
  arrays back into Python via mpheval / mphinterp / mphglobal (nargout=1).
"""

import os
import time
import numpy as np
import matlab.engine

# ---- bridge config (same as 32_Plasma/matlab_data.py) ----
SHORTCUT_PATH = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\COMSOL Multiphysics 6.3"
SHORTCUT_NAME = "COMSOL Multiphysics 6.3 with MATLAB.lnk"
FULL_PATH = os.path.join(SHORTCUT_PATH, SHORTCUT_NAME)

INPUT_MPH_PATH = os.path.normpath(r"D:\32_MoviLSTM\Argon_GEC_CCP\argon_gec_ccp.mph")
OUT_DIR = os.path.normpath(r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted")

# Which expressions to evaluate. Names must match the variables/operators
# defined inside the .mph (open the model in COMSOL -> Model Builder, or run
# the discover_expressions() helper below).
FIELD_EXPRS = ["V", "ne", "Te"]      # field expressions on the mesh
GLOBAL_EXPRS = ["intop1(ne)"]        # global / probe-style expressions


def matlab_init(i_path):
    """Launch COMSOL-with-MATLAB and connect to the shared engine."""
    os.startfile(i_path)
    time.sleep(5)
    sessions = matlab.engine.find_matlab()
    if sessions:
        return matlab.engine.connect_matlab(sessions[0])
    for _ in range(20):
        time.sleep(3)
        sessions = matlab.engine.find_matlab()
        if sessions:
            eng = matlab.engine.connect_matlab(sessions[0])
            eng.eval("disp('Completed')", nargout=0)
            return eng
    raise RuntimeError("Failed to connect to MATLAB session after retries.")


def load_model(eng, mph_path, tag="model"):
    """mphload into a named MATLAB workspace variable."""
    eng.eval(f"{tag} = mphload('{mph_path}');", nargout=0)
    return tag


def discover_expressions(eng, tag="model"):
    """Print plot-group / dataset / variable tags so you know what to ask for.

    mphnavigator(model) opens the model tree GUI; mphtags returns the tag
    list for a given node. Useful when you do not yet know the names of
    the field expressions inside this particular .mph.
    """
    eng.eval(f"disp(mphtags({tag}, 'result'));", nargout=0)
    eng.eval(f"disp(mphtags({tag}.variable));", nargout=0)
    # eng.eval(f"mphnavigator({tag});", nargout=0)  # uncomment for GUI tree


def eval_field(eng, expr, tag="model", dataset=None):
    """mpheval -> numpy arrays of mesh coords + values for one expression.

    Returns (coords, values, time):
        coords : (dim, N)   node coordinates
        values : (T, N)     value at each node, per solution step
        time   : (T,)       solution times (empty for stationary studies)
    """
    args = f"'{expr}'"
    if dataset is not None:
        args += f", 'dataset', '{dataset}'"
    eng.eval(f"d = mpheval({tag}, {args});", nargout=0)
    coords = np.asarray(eng.eval("d.p", nargout=1))
    values = np.asarray(eng.eval("d.d1", nargout=1))
    try:
        t = np.asarray(eng.eval("d.t", nargout=1)).ravel()
    except matlab.engine.MatlabExecutionError:
        t = np.array([])
    return coords, values, t


def eval_global(eng, expr, tag="model"):
    """mphglobal -> 1-D array of a scalar/global expression over time."""
    eng.eval(f"g = mphglobal({tag}, '{expr}');", nargout=0)
    return np.asarray(eng.eval("g", nargout=1)).ravel()


def interp_at_points(eng, expr, points_xyz, tag="model"):
    """mphinterp -> values of `expr` interpolated at user-supplied coordinates.

    points_xyz : (dim, M) numpy array. dim is 2 for 2D models, 3 for 3D.
    """
    pts = matlab.double(points_xyz.tolist())
    eng.workspace["pts"] = pts
    eng.eval(f"v = mphinterp({tag}, '{expr}', 'coord', pts);", nargout=0)
    return np.asarray(eng.eval("v", nargout=1))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    eng = matlab_init(FULL_PATH)
    try:
        load_model(eng, INPUT_MPH_PATH)

        # Uncomment the first time you run on a new .mph:
        # discover_expressions(eng)

        bundle = {}
        for expr in FIELD_EXPRS:
            coords, values, t = eval_field(eng, expr)
            bundle[f"{expr}_coords"] = coords
            bundle[f"{expr}_values"] = values
            bundle[f"{expr}_t"] = t
            print(f"{expr}: coords {coords.shape}, values {values.shape}, t {t.shape}")

        for expr in GLOBAL_EXPRS:
            arr = eval_global(eng, expr)
            safe = expr.replace("(", "_").replace(")", "").replace(" ", "")
            bundle[f"global_{safe}"] = arr
            print(f"{expr}: {arr.shape}")

        out_path = os.path.join(OUT_DIR, "results.npz")
        np.savez_compressed(out_path, **bundle)
        print(f"saved -> {out_path}")
    finally:
        # Detach but leave MATLAB/COMSOL running so the next run reuses it.
        # Call eng.exit() instead if you want to tear the session down.
        pass


if __name__ == "__main__":
    main()
