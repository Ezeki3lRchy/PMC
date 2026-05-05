# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Drives **parameter sweeps over COMSOL Multiphysics models** from Python by piping through MATLAB. Each iteration loads a `.mph` model, sets parameters, runs the study, exports input/output images per case, and saves the resulting `.mph`. The exported image pairs are intended as training data for downstream ML models.

Two active sweep projects live in this repo, each with its own `matlab_data.py`:
- `project_IHCP/` — Inverse Heat Conduction Problem (heat-flux boundary, materials `pm1000` / `sio2` / `ptrh`, heat-flux types `constant` / `sin`).
- `32_Plasma/` — Argon GEC CCP plasma sim (sweeps `pgas` pressure).

The root `matlab_data.py` is the IHCP variant; `32_Plasma/matlab_data.py` is the plasma variant. They share the same launch/connect/sweep skeleton and diverge in paths, parameter names, and the boundary/study identifiers passed to COMSOL.

`model.py` is an unrelated TensorFlow MNIST tutorial and is not part of the pipeline.

## How the Python ↔ MATLAB ↔ COMSOL bridge works

This is the non-obvious part — the launch sequence is fragile and order-dependent:

1. Python calls `os.startfile(...)` on the Windows shortcut **"COMSOL Multiphysics 6.3 with MATLAB.lnk"** (path hardcoded in each `matlab_data.py`). It must be the `.lnk`, not `matlab.exe` — only the COMSOL-with-MATLAB launcher loads the LiveLink classes that `mphload`/`mphrun`/`mphsave` need.
2. COMSOL's bundled `comsolinit.m` (vendor file, copied into `project_IHCP/` for reference) auto-runs and looks for **`comsolstartup.m` in the user's home directory** (`%USERPROFILE%`) or on the MATLAB path.
3. **`matlab.engine.shareEngine` must run somewhere during MATLAB startup.** This is what makes the session discoverable by Python. There are two equally valid places to put it:
   - `comsolstartup.m` in `%USERPROFILE%` (or on MATLAB path) — the COMSOL-recommended hook.
   - `startup.m` in MATLAB's user dir (`%USERPROFILE%\Documents\MATLAB\startup.m`) — MATLAB's native mechanism, runs every session regardless of COMSOL. **This is what the current dev machine actually uses**, alongside `cd D:\32_MoviLSTM\Argon_GEC_CCP` to set the working directory for the plasma sweep.
4. Python sleeps (5–13s), then polls `matlab.engine.find_matlab()` and `connect_matlab()` until the shared session appears (up to 20 retries).

**Implication for edits:** if neither `comsolstartup.m` nor `startup.m` calls `shareEngine`, Python will never connect. The repo's root `comsolstartup.m` is the IHCP-project variant and is **not** what the running setup uses — don't be misled by it. The README's terse hint — "should edited the startup.m for matlab" — refers to this requirement.

The MATLAB code itself is built as Python f-strings inside `eng.eval(""" ... """, nargout=0)`. Curly braces in MATLAB syntax become `{{` `}}` if they're ever needed; right now the scripts only interpolate scalars and paths, so plain `{var}` works.

## Memory leak workaround

COMSOL/MATLAB leak memory across iterations. Every 50 cases, the sweep:
```
eng.exit()
taskkill /F /IM MATLAB.exe
taskkill /F /IM comsolmphserver.exe
matlab_init(...)   # full relaunch
```
When modifying the sweep loop, preserve this counter-based restart — long sweeps without it will OOM.

`model.hist.disable;` in the MATLAB block exists for the same reason (prevents per-iteration model-history accumulation inside a single MATLAB session).

## Running a sweep

There is no test suite, build system, or lint config. Operation is manual:

1. Ensure `comsolstartup.m` is at `%USERPROFILE%\comsolstartup.m` (or on MATLAB path) and points `cd(...)` at the directory containing the target `.mph`.
2. Edit the `material` / `heatflux_type` / `parameter_type` constants near the top of the relevant `matlab_data.py` and confirm the hardcoded `C:\`, `D:\`, `E:\` paths exist on the machine.
3. Confirm the COMSOL shortcut path matches the installed COMSOL version (currently 6.3).
4. `python matlab_data.py` (root, for IHCP) or `python 32_Plasma/matlab_data.py` (for plasma).

Dependencies: `pip install -r requirements.txt` (the key dep is `matlabengine`, which must match the installed MATLAB version — currently `25.1.2`). `environment.yml` is a full conda export of an unrelated `base` env and is not the intended install path.

## Platform constraints

- **Windows-only.** Hardcoded drive letters, `.lnk` shortcuts, `taskkill`, and `os.startfile` are all non-portable. Don't refactor these toward cross-platform unless asked — they reflect the actual deployment.
- **MATLAB engine version must match installed MATLAB.** Bumping `matlabengine` in `requirements.txt` without bumping the MATLAB install (or vice versa) breaks `import matlab.engine`.
- The `generate.ipynb` notebook output shows `ModuleNotFoundError: No module named 'matlab'` — that's a stale kernel state, not a code bug; it just means the notebook was last run in a non-MATLAB venv.

## Conventions when editing the sweep scripts

- The COMSOL identifiers in the f-string MATLAB block (`'ht_PM1000'`, `'hf_BC'`, `'pg3'`, `'anim1'`, `'anim3'`, `'std1'`, `'std2'`, etc.) are **tag names defined inside the `.mph` file**. They are not arbitrary — changing them in Python without changing the model produces silent COMSOL errors. To discover the right tags, open the `.mph` in COMSOL and check the Model Builder tree, or use `mphtags(model, 'result')` (see `project_IHCP/IHCP.m` for an example of building a model from scratch and naming these tags).
- Image export uses `model.result.export('animN').run()`, where `animN` is a pre-configured animation export node in the `.mph`. The Python script only sets `imagefilename`; everything else (frame rate, view, color range) is baked into the model.
