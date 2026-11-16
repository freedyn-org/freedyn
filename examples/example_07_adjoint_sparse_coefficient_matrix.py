"""
Example 7: Sparse coefficient matrix for an adjoint (BDF-like) solver
=====================================================================

Shows the matrix features added for adjoint sensitivity analysis:

- IDENTITY (112): identity matrix with the dimension of MASS
- transposed system matrices (ID + 20):
      DMQDDDQ_T  (122)  = DMQDDDQ'   (102)
      DCQTLIDQ_T (125)  = DCQTLIDQ'  (105)
      DQEXTDQ_T  (128)  = DQEXTDQ'   (108)
      DQEXTDQD_T (129)  = DQEXTDQD'  (109)
      DCQTLEDQ_T (130)  = DCQTLEDQ'  (110)
- set_matrix_scaling(): change the scaling values of an existing matrix.
  The sparsity pattern stays the same, so explicit zeros are kept and a
  scipy CSR matrix can be refreshed in place (no matrix products in Python).

Part 1 checks every transposed ID against the transpose of the original.
Part 2 assembles a block coefficient matrix once and refreshes it in a
backward loop over the stored time steps.

The block structure in build_adjoint_coefficient_matrix() is an EXAMPLE.
Adapt IDs, block positions and coefficients to your own scheme.

Usage:
    python example_07_adjoint_sparse_coefficient_matrix.py <model.fds>
"""

import os
from pathlib import Path
import sys

import numpy as np
from scipy.sparse.linalg import splu
import freedyn as fd

T = fd.analysis.MATRIX_TYPES

DEFAULT_MODEL = (
    Path(__file__).resolve().parent
    / "freedyn_files"
    / "single_mass_oscillator"
    / "single_mass_oscillator.fds"
)


def single_matrix(matrix_name):
    """Create a model matrix containing one sub-matrix at block (0,0)."""
    return fd.analysis.create_matrix(
        np.array([T[matrix_name]], dtype=np.int32),
        np.array([0], dtype=np.int32),
        np.array([0], dtype=np.int32),
        np.array([1.0]),
    )


# ---------------------------------------------------------------------------
# Part 1: transposed matrices and identity
# ---------------------------------------------------------------------------
def verify_transposed_matrices(model, time_index):
    model.update_state_at_index(time_index)
    model.update_jacobian()

    print(f"\nPart 1: transposed IDs vs. transpose of original (time index {time_index})")
    for name in ("DMQDDDQ", "DCQTLIDQ", "DQEXTDQ", "DQEXTDQD", "DCQTLEDQ"):
        A = fd.analysis.get_matrix(single_matrix(name)).toarray()
        A_T = fd.analysis.get_matrix(single_matrix(name + "_T")).toarray()
        err = np.max(np.abs(A_T - A.T)) if A.size else 0.0
        print(f"  {name + '_T':<11} max|A_T - A'| = {err:.3e}   (max|A| = {np.max(np.abs(A)):.3e})")

    I = fd.analysis.get_identity_matrix()
    n_q = model.get_info().num_generalized_coordinates
    print(f"  IDENTITY    shape {I.shape}, equals eye({n_q}): {np.allclose(I.toarray(), np.eye(n_q))}")


# ---------------------------------------------------------------------------
# Part 2: block coefficient matrix, created once, re-scaled per step
# ---------------------------------------------------------------------------
# Example structure (adapt to your scheme), c0, c1, c2 from the step size:
#
#   [ c2*M' + c1*(D - Qext_qd)' + c0*(K + Mqdd_q + CqTl_q - Qext_q)'   Cq' ] [ mu  ]   [ rhs_q ]
#   [ Cq                                                                0  ] [ eta ] = [ rhs_l ]
#
# M, K and D are symmetric, so the original IDs are used for them.
BLOCKS = [
    # (matrix name, block row, block col, coefficient key)
    ("MASS",        0, 0, "c2"),
    ("DAMPING",     0, 0, "c1"),
    ("DQEXTDQD_T",  0, 0, "-c1"),
    ("STIFFNESS",   0, 0, "c0"),
    ("DMQDDDQ_T",   0, 0, "c0"),
    ("DCQTLIDQ_T",  0, 0, "c0"),
    ("DCQTLEDQ_T",  0, 0, "c0"),
    ("DQEXTDQ_T",   0, 0, "-c0"),
    ("CQT",         0, 1, "1"),
    ("CQ",          1, 0, "1"),
]


def scaling_values(h, alpha=1.0):
    """Coefficients of the example scheme for step size h (BDF coefficient alpha)."""
    c0 = 1.0
    c1 = alpha / h
    c2 = (alpha / h) ** 2
    coeff = {"c0": c0, "-c0": -c0, "c1": c1, "-c1": -c1, "c2": c2, "1": 1.0}
    return np.array([coeff[key] for _, _, _, key in BLOCKS])


def build_adjoint_coefficient_matrix(h):
    return fd.analysis.create_matrix(
        np.array([T[name] for name, _, _, _ in BLOCKS], dtype=np.int32),
        np.array([row for _, row, _, _ in BLOCKS], dtype=np.int32),
        np.array([col for _, _, col, _ in BLOCKS], dtype=np.int32),
        scaling_values(h),
    )


def backward_adjoint_loop(model):
    n_steps = model.get_num_time_steps()
    times = np.array([model.get_time_at_index(i) for i in range(n_steps)])

    h0 = times[-1] - times[-2]
    mat_idx = build_adjoint_coefficient_matrix(h0)

    # Pattern is fixed: buffer.sp_mat keeps its structure (also explicit zeros),
    # only the values are refreshed.
    buffer = fd.analysis.ModelRelatedMatrixBuffer(mat_idx, sparse=True)
    nnz = buffer.sp_mat.nnz
    print(f"\nPart 2: coefficient matrix {buffer.sp_mat.shape}, nnz = {nnz}")

    mu = np.zeros(buffer.sp_mat.shape[0])
    for i in range(n_steps - 1, 0, -1):
        h = times[i] - times[i - 1]

        model.update_state_at_index(i)
        model.update_jacobian()

        buffer.set_scaling(scaling_values(h))   # only needed if h changes
        buffer.update_from_dll()
        buffer.apply_to_cached_matrix()
        assert buffer.sp_mat.nnz == nnz

        rhs = np.zeros_like(mu)                # replace with your adjoint right-hand side
        rhs[0] = 1.0
        mu = splu(buffer.sp_mat.tocsc()).solve(rhs)

        if i % max(1, n_steps // 5) == 0:
            print(f"  step {i:5d}  t = {times[i]:.4f}  h = {h:.3e}  |mu| = {np.linalg.norm(mu):.3e}")


def main(argv=None):
    argv = argv or sys.argv
    model_path = Path(argv[1]) if len(argv) > 1 else Path(os.environ.get("FREEDYN_MODEL_PATH", DEFAULT_MODEL))
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        return

    fd.initialize()
    try:
        with fd.Model(model_path, status_output=os.environ.get("FREEDYN_STATUS_OUTPUT", "NO")) as model:
            model.compute_initial_conditions()
            model.solve()
            if model.get_num_time_steps() < 2:
                print("Need at least two time steps.")
                return

            verify_transposed_matrices(model, model.get_num_time_steps() // 2)
            backward_adjoint_loop(model)
    except fd.exceptions.FreeDynError as exc:
        print(f"ERROR: {exc}")
        return

    print("\nExample 07 completed successfully.")


if __name__ == "__main__":
    main()
