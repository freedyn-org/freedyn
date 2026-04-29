"""Reusable matrix buffers for high-frequency C-interface retrieval.

This module hosts internal performance helpers used in optimization loops
to avoid repeated allocation and index-setup overhead.
"""

from ctypes import c_int, c_double, byref, POINTER

import numpy as np
from scipy.sparse import csr_matrix

from . import _core


class ModelMatrixBuffer:
    """Cache matrix structure and only refresh nonzero values from DLL.

    Args:
        matrix_index: Index of model-related matrix in DLL.
        sparse: If True, keep a CSR matrix; else keep a dense matrix.
    """

    __slots__ = [
        "dll",
        "dll_row_ind",
        "dll_col_ind",
        "dll_nonzeros",
        "sparse",
        "flat_idx",
        "dense_mat_flat",
        "dense_mat",
        "sp_mat",
        "c_idx_mat",
    ]

    def __init__(self, matrix_index: int, sparse: bool):
        self.sparse = sparse
        self.dll = _core.get_dll()

        self.dll.getModelRelatedMatrix.argtypes = [
            POINTER(c_int),
            np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
            np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        ]

        mat_num_rows, mat_num_cols, num_nonzeros = _get_matrix_dimensions(matrix_index)

        self.dll_row_ind = np.zeros(mat_num_rows + 1, dtype=c_int)
        self.dll_col_ind = np.zeros(num_nonzeros, dtype=c_int)
        self.dll_nonzeros = np.zeros(num_nonzeros)

        self.c_idx_mat = c_int(matrix_index)
        self.dll.getModelRelatedMatrix(
            byref(self.c_idx_mat), self.dll_row_ind, self.dll_col_ind, self.dll_nonzeros
        )

        # Convert 1-based indices to 0-based.
        col_ind = self.dll_col_ind - 1
        row_ind = self.dll_row_ind - 1

        if self.sparse:
            self.sp_mat = csr_matrix(
                (self.dll_nonzeros, col_ind, row_ind),
                shape=(mat_num_rows, mat_num_cols),
            )
            self.flat_idx = None
            self.dense_mat = None
            self.dense_mat_flat = None
        else:
            dense_mat_rows = np.repeat(np.arange(mat_num_rows), np.diff(row_ind))
            self.flat_idx = dense_mat_rows * mat_num_cols + col_ind
            self.dense_mat = np.zeros((mat_num_rows, mat_num_cols))
            self.dense_mat_flat = self.dense_mat.ravel()
            self.sp_mat = None

    def set_index(self, new_idx: int) -> None:
        """Switch to another existing matrix index with the same structure."""
        self.c_idx_mat.value = new_idx

    def update_from_dll(self) -> None:
        """Refresh nonzero values from DLL for current matrix index."""
        self.dll.getModelRelatedMatrix(
            byref(self.c_idx_mat), self.dll_row_ind, self.dll_col_ind, self.dll_nonzeros
        )

    def apply_to_cached_matrix(self) -> None:
        """Write refreshed values into cached sparse/dense matrix container."""
        if self.sparse:
            self.sp_mat.data[:] = self.dll_nonzeros
        else:
            self.dense_mat_flat[self.flat_idx] = self.dll_nonzeros


def _get_matrix_dimensions(matrix_index: int):
    """Local import helper to avoid circular imports with analysis module."""
    from .analysis import get_matrix_dimensions

    return get_matrix_dimensions(matrix_index)
