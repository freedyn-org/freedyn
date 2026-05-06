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
    FREEDYN_MODEL_PATH        path to model file
    FREEDYN_STATUS_OUTPUT     NO|SCREEN|FILE|SCREENANDFILE (default: NO)
    FREEDYN_RERUN_COUNT       integer number of reruns to execute (default: 1)
    FREEDYN_PARAM_NAME        parameter label for rerun
    FREEDYN_PARAM_VALUE       float value for selected parameter
    FREEDYN_RERUN_END_TIMES   comma-separated end times for reruns, e.g. "0.5,1.0,2.0"
                              omit for full solve; values cycle if fewer than rerun count
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


DEFAULT_MODEL = (
    Path(__file__).resolve().parent
    / "freedyn_files"
    / "single_mass_oscillator"
    / "single_mass_oscillator.fds"
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
    for root in (Path.cwd(),):
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


def resolve_rerun_count(argv):
    # Priority: argv[4] > env var > default
    if len(argv) > 4:
        raw = argv[4]
    else:
        raw = os.environ.get("FREEDYN_RERUN_COUNT", "1")

    rerun_count = int(raw)
    if rerun_count < 1:
        raise ValueError("Rerun count must be >= 1")

    return rerun_count


def solve_and_collect_summary(model, end_time=None):
    model.compute_initial_conditions()
    if end_time is None:
        model.solve()
    else:
        model.solve_until(end_time)

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


def resolve_end_times(argv, rerun_count):
    """Return a list of end times for each rerun, or None for full solve."""
    raw = os.environ.get("FREEDYN_RERUN_END_TIMES")
    if len(argv) > 5:
        raw = argv[5]
    if raw is None:
        return [None] * rerun_count
    # Expect comma-separated floats, e.g. "0.5,1.0,2.0"
    values = [float(v.strip()) for v in raw.split(",")]
    # Cycle or truncate to match rerun_count
    return [values[i % len(values)] for i in range(rerun_count)]


def main(argv=None):
    argv = argv or sys.argv

    model_path = resolve_model_path(argv)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        print("Pass a model path as argv[1] or set FREEDYN_MODEL_PATH.")
        return

    status_output = os.environ.get("FREEDYN_STATUS_OUTPUT", "NO")
    try:
        rerun_count = resolve_rerun_count(argv)
    except ValueError as exc:
        print(f"ERROR: Invalid rerun count: {exc}")
        print("Set FREEDYN_RERUN_COUNT to an integer >= 1 or pass it as argv[4].")
        return

    end_times = resolve_end_times(argv, rerun_count)

    param_name, param_value = resolve_parameter_override(argv)

    print("Initializing FreeDyn...")
    fd.initialize()

    if not verify_rerun_capabilities():
        return

    try:
        with fd.Model(model_path, status_output=status_output) as model:
            print(f"Model loaded: {model_path}")
            print(f"Configured rerun count: {rerun_count}")

            baseline = solve_and_collect_summary(model)
            print_summary("Baseline run", baseline)

            if param_name is not None:
                print(f"\nApplying parameter change: {param_name} = {param_value}")
                model.set_parameter(param_name, param_value)
            else:
                print("\nNo parameter override provided.")
                print("Rerun will still execute using reset_for_rerun() for workflow demonstration.")

            last_rerun = None
            for rerun_idx in range(1, rerun_count + 1):
                end_time = end_times[rerun_idx - 1]
                end_label = f"{end_time:.3f} s" if end_time is not None else "full"
                print(f"\nResetting active model for rerun {rerun_idx}/{rerun_count} (end_time={end_label})...")
                model.reset_for_rerun()

                last_rerun = solve_and_collect_summary(model, end_time=end_time)
                print_summary(f"Rerun {rerun_idx}", last_rerun)

            dq = last_rerun["final_q0"] - baseline["final_q0"]
            print("\nComparison (last rerun vs baseline):")
            print(f"  delta final_Q[0] = {dq:.6e}")
            print(f"  delta steps      = {last_rerun['n_steps'] - baseline['n_steps']}")

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
