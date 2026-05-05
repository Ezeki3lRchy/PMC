"""Discover all ptp.* variables defined on the GEC model."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "32_Plasma"))

import matlab.engine

sessions = matlab.engine.find_matlab()
eng = matlab.engine.connect_matlab(sessions[0])
print("connected")

# Model is already loaded as 'model' in MATLAB workspace from last run
# (extract_one called clear, so reload)
mph = r"D:\32_MoviLSTM\Argon_GEC_CCP\argon_gec_ccp.mph"
eng.eval(f"model = mphload('{mph.replace(chr(92), chr(92)*2)}');", nargout=0)

# Method 1: mphxmeshinfo gives field names of solved variables
print("\n=== mphxmeshinfo fieldnames (solved DOFs) ===")
eng.eval("info = mphxmeshinfo(model);", nargout=0)
try:
    n = int(eng.eval("numel(info.fieldnames)", nargout=1))
    for i in range(1, n + 1):
        name = eng.eval(f"info.fieldnames{{{i}}}", nargout=1)
        print(f"  {name}")
except Exception as e:
    print(f"  fieldnames lookup failed: {e}")

# Method 2: dump full ptp.* variable namespace via a 'who' on a domain
print("\n=== sample ptp.* variables (first dataset, evaluated names) ===")
candidates = [
    # densities and energy
    "ptp.ne", "ptp.Te", "ptp.eps", "ptp.epse", "ptp.we", "ptp.ne_eps",
    "ptp.cAr_1p", "ptp.ni_Ar_1p", "ptp.ni",
    # power deposition
    "ptp.Qrh", "ptp.Pdep", "ptp.Pelec_dep", "ptp.Pe", "ptp.Q_pl", "ptp.Qpl",
    "ptp.Joule", "ptp.Joul",
    # current densities
    "ptp.Je_r", "ptp.Je_z", "ptp.Ji_r", "ptp.Ji_z", "ptp.J_r", "ptp.J_z",
    "ptp.Jc_r", "ptp.Jc_z", "ptp.Jcond_r", "ptp.Jcond_z",
    # electric quantities
    "ptp.E", "ptp.Er", "ptp.Ez", "ptp.normE",
    # known good
    "V", "ptp.ne", "ptp.Re", "ptp.Te",
]
ok, bad = [], []
for c in candidates:
    try:
        eng.eval(f"v = mphmean(model, '{c}', 'volume', 'dataset', 'dset3');", nargout=0)
        ok.append(c)
    except matlab.engine.MatlabExecutionError as e:
        line = str(e).splitlines()[0] if str(e).strip() else "(unknown)"
        bad.append(c)
print("  OK:")
for c in ok:
    print(f"    {c}")
print("  not found:")
for c in bad:
    print(f"    {c}")
