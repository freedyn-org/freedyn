"""
Example 5: Reusing Force Parameter Derivative Buffer
===================================================

Demonstrates how to evaluate dQext/d(param) efficiently by:
- validating parameter labels once
- allocating one dense derivative matrix once
- refreshing all requested parameter columns in-place at sampled states

Usage:
    python example_05_force_parameter_derivative_buffer.py <model.fds> [param_label_1] [param_label_2] ...

If no model path is provided, the script uses the local bundled model:
    examples/freedyn_files/single_mass_oscillator/single_mass_oscillator.fds

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
    for root in (Path.cwd(), Path(r"C:/demos_freedyn")):
        if root.exists():
            candidates.extend(root.rglob("*.fds"))

    if candidates:
        return candidates[0]

    return Path("path_to_your_model.fds")


def resolve_parameter_labels(argv, model):
    if len(argv) > 2:
        return argv[2:]

    available = model.get_parameter_names()
    return available[: min(3, len(available))]


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

            available_parameters = model.get_parameter_names()
            parameter_labels = resolve_parameter_labels(argv, model)
            if not parameter_labels:
                print("Model exposes no parameters. Example 05 cannot build dQext/d(param).")
                return

            unknown = [label for label in parameter_labels if label not in set(available_parameters)]
            if unknown:
                print("ERROR: Unknown parameter label(s):", ", ".join(unknown))
                print("Available labels:", ", ".join(available_parameters) if available_parameters else "<none>")
                return

            print("Using parameter labels:")
            for label in parameter_labels:
                print(f"  - {label}")

            derivative_buffer = fd.analysis.ForceParameterDerivativeMatrixBuffer(
                parameter_labels,
                validate_labels=True,
            )
            row_preview = min(3, derivative_buffer.data.shape[0])

            sample_every = max(1, n_steps // 8)
            print(f"\nSampling every {sample_every} step(s):")
            print("index, time, frobenius_norm, first_column_norm")
            print("Jacobian preview rows: 0 to", row_preview - 1)
            print("Columns:", ", ".join(parameter_labels))

            for i in range(0, n_steps, sample_every):
                model.fetch_states_at_index(i)
                model.update_state_at_index(i)
                time_i = model.t

                derivative_buffer.update_from_dll()
                fro_norm = float(np.linalg.norm(derivative_buffer.data))
                col0_norm = float(np.linalg.norm(derivative_buffer.data[:, 0]))

                print(f"{i}, {time_i:.6f}, {fro_norm:.6e}, {col0_norm:.6e}")
                for r in range(row_preview):
                    row_vals = ", ".join(f"{v:.6e}" for v in derivative_buffer.data[r, :])
                    print(f"  J[{r},:] = [{row_vals}]")

            print("\nDerivative matrix shape:")
            print(f"  {derivative_buffer.data.shape[0]} x {derivative_buffer.data.shape[1]}")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return
    except OSError as exc:
        print(f"ERROR: Native call failed: {exc}")
        return

    print("\nExample 05 completed successfully.")


if __name__ == "__main__":
    main()
