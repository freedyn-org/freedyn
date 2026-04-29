"""
Example 2: Rerun Workflow (with optional parameter change)
===========================================================

Demonstrates a typical rerun sequence:
- initialize DLL
- load model
- run baseline solve
- optionally change one parameter
- call reset_for_rerun()
- solve again and compare results

Usage:
    python example_02_rerun_after_parameter_change.py <model.fds> [param_name] [param_value]

Environment overrides:
    FREEDYN_MODEL_PATH      path to model file
    FREEDYN_STATUS_OUTPUT   NO|SCREEN|FILE|SCREENANDFILE (default: NO)
    FREEDYN_PARAM_NAME      parameter label for rerun
    FREEDYN_PARAM_VALUE     float value for selected parameter
"""

import os
from pathlib import Path
import sys

import freedyn as fd


def verify_rerun_capabilities():
    """Report loaded DLL and verify rerun-related C symbols are present."""
    dll = fd.core.get_dll()
    loaded_dll = getattr(dll, "_name", "<unknown>")
    print(f"Loaded DLL: {loaded_dll}")

    required = ["resetActiveModelForRerun", "updateSystemAtTimeIndex", "getTime"]
    missing = [name for name in required if not hasattr(dll, name)]
    if missing:
        print("ERROR: Loaded DLL does not provide required rerun symbols:")
        for name in missing:
            print(f"  - {name}")
        print("Use the latest rebuilt freedyn.dll and ensure it is the one found by Python.")
        return False

    return True


def resolve_model_path(argv):
    if len(argv) > 1:
        return Path(argv[1])

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


def resolve_parameter_override(argv):
    param_name = os.environ.get("FREEDYN_PARAM_NAME")
    param_value = os.environ.get("FREEDYN_PARAM_VALUE")

    if len(argv) > 2:
        param_name = argv[2]
    if len(argv) > 3:
        param_value = argv[3]

    if not param_name or param_value is None:
        return None, None

    return param_name, float(param_value)


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

    final_time, final_states = model.get_states_at_time(n_steps - 1)
    final_q0 = float(final_states["Q"][0, 0])

    return {
        "n_steps": n_steps,
        "final_time": float(final_time),
        "final_q0": final_q0,
    }


def print_summary(label, summary):
    print(f"{label}:")
    print(f"  steps      = {summary['n_steps']}")
    print(f"  final_time = {summary['final_time']:.6f} s")
    print(f"  final_Q[0] = {summary['final_q0']:.6e}")


def main(argv=None):
    argv = argv or sys.argv

    model_path = resolve_model_path(argv)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        print("Pass a model path as argv[1] or set FREEDYN_MODEL_PATH.")
        return

    status_output = os.environ.get("FREEDYN_STATUS_OUTPUT", "NO")
    param_name, param_value = resolve_parameter_override(argv)

    print("Initializing FreeDyn...")
    fd.initialize()

    if not verify_rerun_capabilities():
        return

    try:
        with fd.Model(model_path, status_output=status_output) as model:
            print(f"Model loaded: {model_path}")

            baseline = solve_and_collect_summary(model)
            print_summary("Baseline run", baseline)

            if param_name is not None:
                print(f"\nApplying parameter change: {param_name} = {param_value}")
                model.set_parameter(param_name, param_value)
            else:
                print("\nNo parameter override provided.")
                print("Rerun will still execute using reset_for_rerun() for workflow demonstration.")

            print("Resetting active model for rerun...")
            model.reset_for_rerun()

            rerun = solve_and_collect_summary(model)
            print_summary("Rerun", rerun)

            dq = rerun["final_q0"] - baseline["final_q0"]
            print("\nComparison:")
            print(f"  delta final_Q[0] = {dq:.6e}")
            print(f"  delta steps      = {rerun['n_steps'] - baseline['n_steps']}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        print("Tip: make sure your installed freedyn package loads a matching DLL build and try FREEDYN_STATUS_OUTPUT=NO")
        return

    print("\nExample 02 completed successfully.")


if __name__ == "__main__":
    main()
