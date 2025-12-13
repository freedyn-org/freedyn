# Getting Started with FreeDyn v1.0.0

This guide covers installation, a first run, and common tasks with the current Python API.

## Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Python Setup](#python-setup)
- [First Run](#first-run)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Support](#support)

## Prerequisites

- Windows 7 or later (64-bit recommended)
- Python 3.8 or later
- freedyn.dll (included in the release)
- Visual C++ Redistributable (included in the release)

## Installation

1. Download the release zip: https://github.com/freedyn-org/freedyn/releases
2. Extract (example layout):
   ```
   C:\FreeDyn\
   ├── bin\                  # freedyn.dll and dependencies
   ├── bindings\python\      # Python API
   ├── examples\             # Example scripts
   ├── docs\                 # Documentation
   ├── setup.py
   └── README.md
   ```
3. Install the Python package:
   ```bash
   cd C:\FreeDyn
   pip install .
   ```
   For editable/development installs:
   ```bash
   pip install -e .
   ```
4. (Optional) Manual path instead of install:
   ```python
   import sys
   sys.path.insert(0, r"C:\FreeDyn\bindings\python")
   ```

## Python Setup

Create a virtual environment (recommended):
```bash
python -m venv freedyn_env
freedyn_env\Scripts\activate
pip install .
```

## First Run

### CLI
```bash
freedyn-run C:\path\to\model.fds
```

### Python
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

## Common Tasks

All examples assume `fd.initialize()` and an active `model` context.

### Extract matrices
```python
states = model.create_state_vectors()
time, states = model.get_states_at_time(0)

M = fd.analysis.get_mass_matrix(states)
K = fd.analysis.get_stiffness_matrix(states)
D = fd.analysis.get_damping_matrix(states)

print(M.shape, K.shape, D.shape)
```

### Force vectors
```python
states = model.create_state_vectors()
time, states = model.get_states_at_time(0)

f_ext = fd.analysis.get_physical_dof_vector('SUMOFEXTFORCES', time, states)
f_all = fd.analysis.get_physical_dof_vector('SUMOFALLFORCES', time, states)
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

### "freedyn.dll not found"
1. Verify `bin/freedyn.dll` exists.
2. Add bin to PATH before importing:
   ```python
   import os
   os.environ['PATH'] = r"C:\FreeDyn\bin;" + os.environ['PATH']
   ```
3. Reinstall VC++ redistributable (included in release or https://support.microsoft.com/en-us/help/2977003).

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
