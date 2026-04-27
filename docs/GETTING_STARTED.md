# Getting Started with FreeDyn

This guide covers installation and first steps – both for GUI users and Python developers.

## Contents

- [Download](#download)
- [Installation (GUI)](#installation-gui)
- [Installation (Python Bindings)](#installation-python-bindings)
- [First Run – GUI](#first-run--gui)
- [First Run – Python](#first-run--python)
- [State Model](#state-model)
- [Common Tasks (Python)](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Support](#support)

## Download

Download the latest release ZIP from **[GitHub Releases](https://github.com/freedyn-org/freedyn/releases)**.

Extract it to a location of your choice, e.g. `C:\FreeDyn`. The extracted folder contains:

```
C:\FreeDyn\
├── bin\
│   ├── x64_MD\              # MD variant: Freedyn_GUI.exe, freedyn.dll, dependencies
│   └── x64_MT\              # MT variant: static CRT build
├── bindings\python\         # Python API (source code)
├── examples\                # Example scripts (Python)
├── docs\                    # Documentation
├── setup.py
└── README.md
```

## Installation (GUI)

No installation required. After extracting the ZIP:

1. Navigate to the `bin\x64_MD\` folder
2. Double-click **`Freedyn_GUI.exe`**

**Prerequisites (all included in the release):**
- Windows 7 or later (64-bit)
- Visual C++ Redistributable
- Intel MKL runtime

If Windows reports missing DLLs, install the Visual C++ Redistributable from
the release folder or from https://support.microsoft.com/en-us/help/2977003.

## Installation (Python Bindings)

The Python bindings are optional – install them if you want scripting,
automation, or advanced analysis capabilities.

**Prerequisites:**
- Python 3.8 or later
- The extracted release (see above)

From the extracted release directory:
```bash
cd C:\FreeDyn
pip install .
```

For editable/development installs:
```bash
pip install -e .
```

**Recommended:** use a virtual environment:
```bash
python -m venv freedyn_env
freedyn_env\Scripts\activate
pip install .
```

(Optional) Use the Python API without installing:
```python
import sys
sys.path.insert(0, r"C:\FreeDyn\bindings\python")
```

## First Run – GUI

1. Start `Freedyn_GUI.exe` from the `bin\x64_MD\` folder
2. Open a model file (`.fds`) via **File → Open**
3. Configure simulation settings and run

The GUI provides pre-processing (model setup, visualization) and
post-processing (result plots, animation).

## First Run – Python

### CLI
```bash
freedyn-run C:\path\to\model.fds
```

### Script
Create `my_first_simulation.py`:
```python
import freedyn as fd
from pathlib import Path

model_path = Path(r"C:\path\to\your_model.fds")

fd.initialize()  # loads freedyn.dll (with legacy fallback)

with fd.Model(model_path, status_output="SCREEN") as model:
    info = model.get_info()
    print(f"Loaded: {info}")

    model.compute_initial_conditions()
    model.solve()

    total_steps = model.get_num_time_steps()
    print(f"Total steps: {total_steps}")

    for idx, time, states in model.iterate_time_steps():
        if idx % 10:
            continue
        q0 = states["Q"][0, 0]
        print(f"Step {idx}: t={time:.4f} s, Q[0]={q0:.6e}")
```
Run it:
```bash
python my_first_simulation.py
```

## State Model

FreeDyn uses a **cached-state architecture**: the DLL holds one current system
state internally. All query functions (matrices, force vectors, measures, …)
operate on that cached state. There are two ways the cache gets set:

1. **After the solver ran** — `model.solve()` or `model.solve_until(t)` leave
   the system at the last computed time step. All query functions can be called
   immediately without an explicit `update_system` call.

2. **Arbitrary state (post-processing / optimization)** — call
   `fd.update_system(time, states)` first, then call any query functions.
   This is the typical pattern when iterating over stored results:

```python
for idx, time, states in model.iterate_time_steps():
    fd.update_system(time, states)   # sets the cached state
    M = fd.analysis.get_mass_matrix()
    f = fd.analysis.get_physical_dof_vector('SUMOFALLFORCES')
```

`update_system` is **not** a solver step — it only evaluates kinematics and
forces at the given state without advancing time.

## Common Tasks

All examples assume `fd.initialize()` and an active `model` context.

### Extract matrices
```python
states = model.create_state_vectors()
time, states = model.get_states_at_time(0)
fd.update_system(time, states)

M = fd.analysis.get_mass_matrix()
K = fd.analysis.get_stiffness_matrix()
D = fd.analysis.get_damping_matrix()

print(M.shape, K.shape, D.shape)
```

### Force vectors
```python
states = model.create_state_vectors()
time, states = model.get_states_at_time(0)
fd.update_system(time, states)

f_ext = fd.analysis.get_physical_dof_vector('SUMOFEXTFORCES')
f_all = fd.analysis.get_physical_dof_vector('SUMOFALLFORCES')
```

### Parameters and splines
```python
model.set_parameter("spring_stiffness", 1000.0)
model.set_spline("load_curve", x_values, y_values)  # x_values, y_values are numpy arrays
```

### Measures
```python
names = model.get_measure_names()
if names:
    val = model.get_measure_value(names[0])
    print(names[0], val)
```

## Troubleshooting

### Freedyn_GUI.exe does not start
1. Make sure all files from the release ZIP are extracted (do not run from inside the ZIP).
2. Check that `freedyn.dll` and other DLLs are in the same folder as `Freedyn_GUI.exe` (`bin\x64_MD\`).
3. Install the Visual C++ Redistributable (included in release or from https://support.microsoft.com/en-us/help/2977003).

### "freedyn.dll not found" (Python)
1. Verify `bin/freedyn.dll` exists in the extracted release.
2. Add bin to PATH before importing:
   ```python
   import os
   os.environ['PATH'] = r"C:\FreeDyn\bin;" + os.environ['PATH']
   ```
3. Reinstall VC++ redistributable (see above).

### "Model creation failed"
1. Check the `.fds` path is correct and accessible.
2. Use an absolute path.
3. Enable `status_output="SCREEN"` for diagnostics.

### "No module named 'freedyn'"
1. Confirm install: `pip show freedyn`.
2. If missing, reinstall from the extracted release directory: `pip install .`.
3. As a fallback, add `bindings/python` to `sys.path` as shown above.

### Slow performance
1. Large models need more RAM/CPU; close other heavy apps.
2. Reduce output frequency in the model.
3. For partial runs, use `model.solve_until(t)` instead of full `model.solve()`.

## Examples

- `examples/example_01_basic_simulation.py` - basic load/solve/iterate

## Support

- Issues: https://github.com/freedyn-org/freedyn/issues
- Documentation updates: https://github.com/freedyn-org/freedyn/wiki

---

Ready to run? Try the CLI with your `.fds` file or the basic example script.
