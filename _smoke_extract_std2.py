"""Smoke test: run extract_std2.extract_one() on the single tutorial .mph."""
import os
import sys
import time

# make `from extract_std2 import ...` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "32_Plasma"))

from extract_std2 import matlab_init, extract_one  # noqa: E402

MPH = r"D:\32_MoviLSTM\Argon_GEC_CCP\argon_gec_ccp.mph"
OUT_DIR = r"D:\32_MoviLSTM\Argon_GEC_CCP\extracted_std2"
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "argon_gec_ccp.npz")

t0 = time.time()
print(f"connecting to MATLAB...")
eng = matlab_init()
print(f"connected ({time.time() - t0:.1f}s)")

print(f"extracting std2 -> {out}")
t1 = time.time()
extract_one(eng, MPH, out)
print(f"done ({time.time() - t1:.1f}s extraction; {time.time() - t0:.1f}s total)")

# show what came out
import numpy as np
d = np.load(out, allow_pickle=True)
print("\nkeys + shapes:")
for k in d.files:
    a = d[k]
    print(f"  {k:<28} {a.shape}  {a.dtype}")
print(f"\nsize on disk: {os.path.getsize(out) / 1e6:.2f} MB")
