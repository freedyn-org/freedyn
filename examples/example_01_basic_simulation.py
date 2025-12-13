"""
Example 1: Basic Simulation
===========================

Minimal end-to-end run with the high-level FreeDyn API:
- initialize the DLL
- load a model
- solve
- iterate results

Run it with a model path argument or the FREEDYN_MODEL_PATH env var, for example:
    python example_01_basic_simulation.py "C:/path/to/model.fds"
"""

import os
from pathlib import Path
import sys

import freedyn as fd


def resolve_model_path(argv):
    if len(argv) > 1:
        return Path(argv[1])
    env_path = os.environ.get("FREEDYN_MODEL_PATH")
    if env_path:
        return Path(env_path)
    return Path("path_to_your_model.fds")


def main(argv=None):
    argv = argv or sys.argv

    model_path = resolve_model_path(argv)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        print("Pass a model path as argv[1] or set FREEDYN_MODEL_PATH.")
        return

    print("Initializing FreeDyn...")
    try:
        fd.initialize()
    except fd.exceptions.DLLLoadError as exc:
        print(f"ERROR: {exc}")
        print("Ensure freedyn.dll is available (packaged in freedyn/bin).")
        return

    try:
        with fd.Model(model_path, status_output="SCREEN") as model:
            info = model.get_info()
            print(f"\nModel loaded: {info}")

            print("\nComputing initial conditions...")
            model.compute_initial_conditions()

            print("Solving equations of motion...")
            model.solve()

            total_steps = model.get_num_time_steps()
            print(f"\nSimulation complete: {total_steps} time steps")

            print("\nSampled results (every 10th step):")
            for idx, time, states in model.iterate_time_steps():
                if idx % 10:
                    continue
                q0 = states["Q"][1, 0]
                print(f"  Step {idx:4d}: t={time:8.4f} s, Q[0]={q0:12.6e}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return

    print("\nExample completed successfully.")


if __name__ == "__main__":
    main()
