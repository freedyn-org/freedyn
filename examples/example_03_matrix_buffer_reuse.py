"""
Example 3: Reusing ModelRelatedMatrixBuffer
==========================================

Demonstrates how to reduce allocation overhead in analysis loops by:
- creating a model-related matrix once
- creating a reusable matrix buffer once
- updating only matrix values for each sampled state

Usage:
    python example_03_matrix_buffer_reuse.py <model.fds>

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


def build_mass_matrix_index():
    matrix_ids = np.array([fd.analysis.MATRIX_TYPES["MASS"], fd.analysis.MATRIX_TYPES["MASS"]], dtype=np.int32)
    row_pos = np.array([0, 0], dtype=np.int32)
    col_pos = np.array([0, 1], dtype=np.int32)
    scales = np.array([1.0, 1.0], dtype=np.float64)
    return fd.analysis.create_matrix(matrix_ids, row_pos, col_pos, scales)


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

            matrix_idx = build_mass_matrix_index()

            # One sparse and one dense buffer using identical matrix structure.
            sparse_buffer = fd.analysis.ModelRelatedMatrixBuffer(matrix_idx, sparse=True)
            dense_buffer = fd.analysis.ModelRelatedMatrixBuffer(matrix_idx, sparse=False)

            sample_every = max(1, n_steps // 8)
            print(f"\nSampling every {sample_every} step(s):")
            print("index, mass_trace_sparse, mass_trace_dense")

            for i in range(0, n_steps, sample_every):
                model.update_state_at_index(i)
                model.update_jacobian()

                sparse_buffer.update_from_dll()
                sparse_buffer.apply_to_cached_matrix()

                dense_buffer.update_from_dll()
                dense_buffer.apply_to_cached_matrix()

                # Compare a simple metric from both cached forms.
                trace_sparse = float(sparse_buffer.sp_mat.diagonal().sum())
                trace_dense = float(np.trace(dense_buffer.dense_mat))

                print(f"{i}, {trace_sparse:.6e}, {trace_dense:.6e}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        return

    print("\nExample 03 completed successfully.")


if __name__ == "__main__":
    main()
