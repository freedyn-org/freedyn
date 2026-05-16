"""Minimal command-line entry point for FreeDyn simulations."""

import argparse
from pathlib import Path
import sys

import freedyn as fd


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a FreeDyn .fds model")
    parser.add_argument("model", help="Path to .fds model file")
    parser.add_argument(
        "--status",
        choices=["SCREEN", "FILE", "NO", "SCREENANDFILE"],
        default="SCREEN",
        help="FreeDyn status output mode",
    )
    args = parser.parse_args(argv)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        return 1

    try:
        fd.initialize()
    except fd.exceptions.DLLLoadError as exc:
        print(f"ERROR: {exc}")
        return 1

    try:
        with fd.Model(model_path, status_output=args.status) as model:
            info = model.get_info()
            print(f"Model loaded: {info}")
            print("Computing initial conditions...")
            model.compute_initial_conditions()
            print("Solving equations of motion...")
            model.solve()
            steps = model.get_num_time_steps()
            print(f"Simulation complete with {steps} time steps.")

            print("Sample results (first 5 steps):")
            for idx in model.iterate_time_steps():
                if idx >= 5:
                    break
                q0 = model.Q[0, 0]
                print(f"  Step {idx:3d}: t={model.t:8.4f} s, Q[0]={q0:12.6e}")
            if steps > 5:
                print(f"  ... (showing 5 of {steps} steps)")

    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
