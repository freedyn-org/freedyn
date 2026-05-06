"""
Example 4: Reusing Force/Constraint Vector Buffers
==================================================

Demonstrates how to reduce allocation overhead in analysis loops by:
- creating reusable vector buffers once
- updating only their values for sampled states
- reading buffer contents without re-allocating arrays each call

Usage:
    python example_04_vector_buffer_reuse.py <model.fds>

Environment overrides:
    FREEDYN_MODEL_PATH      path to model file
    FREEDYN_STATUS_OUTPUT   NO|SCREEN|FILE|SCREENANDFILE (default: NO)
"""

import os
from pathlib import Path
import sys

import numpy as np
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

    candidates = []
    for root in (Path.cwd(),):
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
            print(f"Model loaded: {model_path}")

            model.compute_initial_conditions()
            model.solve()

            n_steps = model.get_num_time_steps()
            if n_steps <= 0:
                print("No time steps available.")
                return

            force_buffer = fd.analysis.ForceVectorBuffer("MBS_SUMOFALLFORCES")
            constraint_buffer = None
            if model.get_info().num_lagrange_multipliers > 0:
                constraint_buffer = fd.analysis.ConstraintVectorBuffer("MBS_CONSTRERROR")

            sample_every = max(1, n_steps // 8)
            print(f"\nSampling every {sample_every} step(s):")
            if constraint_buffer is None:
                print("index, time, force_norm")
            else:
                print("index, time, force_norm, constraint_norm")

            for i in range(0, n_steps, sample_every):
                model.fetch_states_at_index(i)
                model.update_state_at_index(i)
                time_i = model.t

                force_buffer.update_from_dll()
                force_norm = float(np.linalg.norm(force_buffer.data))

                if constraint_buffer is None:
                    print(f"{i}, {time_i:.6f}, {force_norm:.6e}")
                    continue

                constraint_buffer.update_from_dll()
                constraint_norm = float(np.linalg.norm(constraint_buffer.data))
                print(f"{i}, {time_i:.6f}, {force_norm:.6e}, {constraint_norm:.6e}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        return

    print("\nExample 04 completed successfully.")


if __name__ == "__main__":
    main()
