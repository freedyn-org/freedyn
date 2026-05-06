"""
Example 6: Rerun Workflow with Spline Control Update
====================================================

Demonstrates the recommended workflow for control updates via spline data:
- load model
- baseline solve
- update control spline via set_spline(...)
- call reset_for_rerun()
- solve again and compare results

Usage:
    python example_06_spline_rerun.py <model.fds> [spline_name]

If no model path is provided, the script uses the local bundled model:
    examples/freedyn_files/spline_control_oscillator/spline_control_oscillator.fds

Environment overrides:
    FREEDYN_MODEL_PATH        path to model file
    FREEDYN_STATUS_OUTPUT     NO|SCREEN|FILE|SCREENANDFILE (default: NO)
    FREEDYN_SPLINE_NAME       spline label to update (default: data)
    FREEDYN_CTRL_NODES        number of control grid points (default: 12)
    FREEDYN_CTRL_AMPLITUDE    control amplitude for second rerun (default: 5.0)
"""

import os
from pathlib import Path
import sys

import numpy as np
import freedyn as fd


DEFAULT_MODEL = (
    Path(__file__).resolve().parent
    / "freedyn_files"
    / "spline_control_oscillator"
    / "spline_control_oscillator.fds"
)


def resolve_model_path(argv):
    if len(argv) > 1:
        return Path(argv[1])

    if DEFAULT_MODEL.exists():
        return DEFAULT_MODEL

    env_path = os.environ.get("FREEDYN_MODEL_PATH")
    if env_path:
        return Path(env_path)

    candidates = []
    for root in (Path.cwd(), Path(r"C:/demos_freedyn")):
        if root.exists():
            candidates.extend(root.rglob("*.fds"))

    if candidates:
        return candidates[0]

    return Path("path_to_your_model.fds")


def resolve_spline_name(argv):
    if len(argv) > 2:
        return argv[2]
    return os.environ.get("FREEDYN_SPLINE_NAME", "data")


def solve_and_collect_summary(model):
    model.compute_initial_conditions()
    model.solve()

    n_steps = model.get_num_time_steps()
    if n_steps <= 0:
        return {
            "n_steps": 0,
            "final_time": 0.0,
            "final_q0": 0.0,
        }

    model.fetch_states_at_index(n_steps - 1)
    final_q0 = float(model.Q[0, 0])

    return {
        "n_steps": n_steps,
        "final_time": float(model.t),
        "final_q0": final_q0,
    }


def print_summary(label, summary):
    print(f"{label}:")
    print(f"  steps      = {summary['n_steps']}")
    print(f"  final_time = {summary['final_time']:.6f} s")
    print(f"  final_Q[0] = {summary['final_q0']:.6e}")


def build_control_profiles(sim_end: float, n_nodes: int, amplitude: float):
    t = np.linspace(0.0, sim_end, n_nodes)

    profile_zero = np.zeros_like(t)

    # Triangle profile for visible rerun effect.
    mid = 0.5 * sim_end
    profile_triangle = np.where(
        t <= mid,
        amplitude * (t / max(mid, 1e-12)),
        amplitude * (1.0 - (t - mid) / max(sim_end - mid, 1e-12)),
    )

    return t, profile_zero, profile_triangle


def main(argv=None):
    argv = argv or sys.argv

    model_path = resolve_model_path(argv)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        print("Pass a model path as argv[1] or set FREEDYN_MODEL_PATH.")
        return

    spline_name = resolve_spline_name(argv)
    status_output = os.environ.get("FREEDYN_STATUS_OUTPUT", "NO")
    n_nodes = int(os.environ.get("FREEDYN_CTRL_NODES", "12"))
    amplitude = float(os.environ.get("FREEDYN_CTRL_AMPLITUDE", "5.0"))

    if n_nodes < 2:
        print("ERROR: FREEDYN_CTRL_NODES must be >= 2")
        return

    print("Initializing FreeDyn...")
    fd.initialize()

    try:
        with fd.Model(model_path, status_output=status_output) as model:
            print(f"Model loaded: {model_path}")
            print(f"Spline label: {spline_name}")

            baseline = solve_and_collect_summary(model)
            print_summary("Baseline run", baseline)

            sim_end = baseline["final_time"] if baseline["final_time"] > 0.0 else 10.0
            t, u0, u1 = build_control_profiles(sim_end, n_nodes, amplitude)

            print("\nApplying spline update (rerun #1): zero profile")
            model.set_spline(spline_name, t, u0)
            model.reset_for_rerun()
            rerun1 = solve_and_collect_summary(model)
            print_summary("Rerun #1", rerun1)

            print("\nApplying spline update (rerun #2): triangle profile")
            model.set_spline(spline_name, t, u1)
            model.reset_for_rerun()
            rerun2 = solve_and_collect_summary(model)
            print_summary("Rerun #2", rerun2)

            print("\nComparison (Rerun #2 vs Baseline):")
            print(f"  delta final_Q[0] = {rerun2['final_q0'] - baseline['final_q0']:.6e}")
            print(f"  delta steps      = {rerun2['n_steps'] - baseline['n_steps']}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        print("Tip: verify spline label exists in model and force expression depends on that spline.")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        return

    print("\nExample 06 completed successfully.")


if __name__ == "__main__":
    main()
