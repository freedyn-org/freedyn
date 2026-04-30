"""
Example 1: Basic Simulation
===========================

Practical end-to-end run with the high-level FreeDyn API:
- initialize the DLL
- load a model (.fds)
- solve
- iterate states
- run analysis queries on cached states

Run it with a model path argument or the FREEDYN_MODEL_PATH env var, for example:
    python example_01_basic_simulation.py "C:/path/to/model.fds"
"""

import os
from pathlib import Path
import sys

import freedyn as fd


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

    # Development convenience: pick first .fds from common local locations.
    candidates = []
    for root in (Path.cwd(), Path(r"C:/demos_freedyn")):
        if root.exists():
            candidates.extend(root.rglob("*.fds"))

    if candidates:
        return candidates[0]

    return Path("path_to_your_model.fds")


def main(argv=None):
    argv = argv or sys.argv

    model_path = resolve_model_path(argv)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        print("Pass a model path as argv[1] or set FREEDYN_MODEL_PATH.")
        return

    status_output = os.environ.get("FREEDYN_STATUS_OUTPUT", "NO")

    print("Initializing FreeDyn...")
    fd.initialize()

    try:
        with fd.Model(model_path, status_output=status_output) as model:
            info = model.get_info()
            print(f"\nModel loaded: {info}")

            print("\nComputing initial conditions...")
            model.compute_initial_conditions()

            print("Solving equations of motion...")
            model.solve()

            total_steps = model.get_num_time_steps()
            print(f"\nSimulation complete: {total_steps} time steps")

            sample_every = max(1, total_steps // 20)
            print(f"\nSampled results (every {sample_every} step(s), max ~20 lines):")
            for idx, time, states in model.iterate_time_steps():
                if idx % sample_every:
                    continue
                q0 = states["Q"][0, 0]
                print(f"  Step {idx:4d}: t={time:8.4f} s, Q[0]={q0:12.6e}")

            if total_steps > 0:
                sample_idx = min(10, total_steps - 1)
                sample_time, sample_states = model.get_states_at_time(sample_idx)

                # Query functions operate on DLL-cached state, so set it first.
                fd.core.update_system(sample_time, sample_states)
                mass = fd.analysis.get_mass_matrix()
                f_all = fd.analysis.get_force_vector("SUMOFALLFORCES")

                print("\nAnalysis at sampled state:")
                print(f"  index={sample_idx}, time={sample_time:.6f} s")
                print(f"  mass matrix shape: {mass.shape}")
                print(f"  force vector shape: {f_all.shape}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        print("Tip: make sure your installed freedyn package loads a matching DLL build and try FREEDYN_STATUS_OUTPUT=NO")
        return

    print("\nExample 01 completed successfully.")


if __name__ == "__main__":
    main()
