"""
Advanced analysis functions for FreeDyn models.

Matrix and vector extraction, Jacobian computations, and advanced
dynamics analysis.
"""

from typing import List, Tuple
from ctypes import c_int, c_double, c_char_p, byref, POINTER
import numpy as np
from scipy.sparse import csr_matrix

from . import _core
from .exceptions import MatrixError, ConstraintError


# Matrix type identifiers
MATRIX_TYPES = {
    "MASS": 101,                    # Global mass matrix M(q)
    "DMQDDDQ": 102,                 # d(M(q)*qdd)/dq
    "DQVVDQ": 103,                  # d(Qvv(q,qd))/dq
    "DQVVDQD": 104,                 # d(Qvv(q,qd))/dqd
    "DCQTLIDQ": 105,                # d(Cq(q)'*l)/dq (internal)
    "STIFFNESS": 106,               # Stiffness matrix K
    "DAMPING": 107,                 # Damping matrix D
    "DQEXTDQ": 108,                 # d(QExt(q,qd))/dq
    "DQEXTDQD": 109,                # d(QExt(q,qd))/dqd
    "DCQTLEDQ": 110,                # d(Cq(q)'*l)/dq (external)
    "ABAR": 111,                    # A_bar matrix for kinematics
    "CQT": 201,                     # d(c(q))/dq transposed
    "CQTDT": 202,                   # d/dt(d(c(q))/dq) transposed
    "CQ": 301,                      # d(c(q))/dq
    "CQDT": 302                     # d/dt(d(c(q))/dq)
}

# Vector type identifiers
VECTOR_TYPES = {
    "ACCINERTIAFORCE": "MBS_ACCINERTIAFORCE",       # Acceleration inertia forces
    "CONSTRFORCE": "MBS_CONSTRFORCE",               # Constraint forces
    "VELINERTIAFORCE": "MBS_VELINERTIAFORCE",       # Velocity inertia forces
    "SUMOFEXTFORCES": "MBS_SUMOFEXTFORCES",         # Sum of external forces
    "ELASTICFORCES": "MBS_ELASTICFORCES",           # Elastic forces
    "DAMPINGFORCES": "MBS_DAMPINGFORCES",           # Damping forces
    "SUMOFALLFORCES": "MBS_SUMOFALLFORCES",         # Sum of all forces
}


def get_physical_dof_vector(
    vector_type: str,
) -> np.ndarray:
    """Get force or dynamics-related vector for physical DOFs.

    The system must already be at the desired state via update_system() or
    because the solver just placed it there.

    Args:
        vector_type: Type of vector ('ACCINERTIAFORCE', 'CONSTRFORCE', etc.)

    Returns:
        Numpy array of the requested vector

    Raises:
        ConstraintError: If computation fails
    """
    dll = _core.get_dll()

    if vector_type not in VECTOR_TYPES:
        raise ValueError(f"Unknown vector type: {vector_type}")

    c_vector_type = c_char_p(VECTOR_TYPES[vector_type].encode("utf-8"))
    c_success = c_int(-1)

    info = _core.get_model_info()
    q_vec = np.zeros((info["numGeneralizedCoordinates"], 1))

    dll.getForceVector.argtypes = [
        c_char_p,
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        POINTER(c_int)
    ]
    dll.getForceVector(c_vector_type, q_vec, byref(c_success))
    
    if c_success.value <= 0:
        raise ConstraintError(f"Failed to compute {vector_type} vector")
    
    return q_vec


def get_constraint_vector(
    vector_type: str,
) -> np.ndarray:
    """Get constraint-related vector (Lagrange multipliers, errors, etc.).

    The system must already be at the desired state via update_system() or
    because the solver just placed it there.

    Args:
        vector_type: Type of vector ('CONSTRERROR', 'DCONSTRDT', etc.)

    Returns:
        Numpy array of constraint values

    Raises:
        ConstraintError: If computation fails
    """
    dll = _core.get_dll()

    constraint_types = {
        "CONSTRERROR": "MBS_CONSTRERROR",           # Constraint equation residuum
        "DCONSTRDT": "MBS_DCONSTRDT",               # Time derivative
        "DCQDTMULTQD": "MBS_DCQDTMULTQD",           # Cqd*Qd
        "D2CONSTRDT2": "MBS_D2CONSTRDT2",           # Second time derivative
    }

    if vector_type not in constraint_types:
        raise ValueError(f"Unknown constraint vector type: {vector_type}")

    c_vector_type = c_char_p(constraint_types[vector_type].encode("utf-8"))
    c_success = c_int(-1)

    info = _core.get_model_info()
    l_vec = np.zeros((info["numLagrangeMultipliers"], 1))

    dll.getConstraintVector.argtypes = [
        c_char_p,
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        POINTER(c_int)
    ]
    dll.getConstraintVector(c_vector_type, l_vec, byref(c_success))
    
    if c_success.value <= 0:
        raise ConstraintError(f"Failed to compute {vector_type} vector")
    
    return l_vec


def create_matrix(
    matrix_ids: np.ndarray,
    row_positions: np.ndarray,
    col_positions: np.ndarray,
    scaling_values: np.ndarray
) -> int:
    """Create a custom model matrix by mapping component matrices.
    
    Args:
        matrix_ids: Array of matrix type IDs (see MATRIX_TYPES)
        row_positions: Row positions where matrices map (0-based)
        col_positions: Column positions where matrices map (0-based)
        scaling_values: Scaling factors for each matrix
        
    Returns:
        Matrix index for later retrieval
        
    Raises:
        MatrixError: If matrix creation fails
    """
    dll = _core.get_dll()
    
    c_num_rows = c_int(np.max(row_positions) + 1)
    c_num_cols = c_int(np.max(col_positions) + 1)
    c_num_matrices = c_int(matrix_ids.shape[0])
    c_matrix_idx = c_int(-1)
    
    dll.createModelRelatedMatrix.argtypes = [
        POINTER(c_int),
        POINTER(c_int),
        POINTER(c_int),
        np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        POINTER(c_int)
    ]
    dll.createModelRelatedMatrix(
        byref(c_num_rows), byref(c_num_cols), byref(c_num_matrices),
        matrix_ids, row_positions, col_positions, scaling_values,
        byref(c_matrix_idx)
    )
    
    if c_matrix_idx.value < 0:
        raise MatrixError("Failed to create model matrix")
    
    return c_matrix_idx.value


def get_matrix_dimensions(matrix_index: int) -> Tuple[int, int, int]:
    """Get dimensions of a model matrix.
    
    Args:
        matrix_index: Index returned by create_matrix()
        
    Returns:
        Tuple of (num_rows, num_cols, num_non_zeros)
        
    Raises:
        MatrixError: If matrix invalid
    """
    dll = _core.get_dll()
    
    c_matrix_idx = c_int(matrix_index)
    c_num_rows = c_int(0)
    c_num_cols = c_int(0)
    c_num_nonzeros = c_int(0)
    
    dll.getDimOfModelRelatedMatrix.argtypes = [
        POINTER(c_int),
        POINTER(c_int),
        POINTER(c_int),
        POINTER(c_int)
    ]
    dll.getDimOfModelRelatedMatrix(
        byref(c_matrix_idx), byref(c_num_rows),
        byref(c_num_cols), byref(c_num_nonzeros)
    )
    
    if c_num_rows.value <= 0:
        raise MatrixError(f"Invalid matrix index: {matrix_index}")
    
    return c_num_rows.value, c_num_cols.value, c_num_nonzeros.value


def get_matrix(matrix_index: int) -> csr_matrix:
    """Get model matrix as scipy sparse CSR format.
    
    Args:
        matrix_index: Index returned by create_matrix()
        
    Returns:
        scipy.sparse.csr_matrix
        
    Raises:
        MatrixError: If retrieval fails
    """
    dll = _core.get_dll()
    
    num_rows, num_cols, num_nonzeros = get_matrix_dimensions(matrix_index)
    
    row_ind = np.zeros(num_rows + 1, dtype=c_int)
    col_ind = np.zeros(num_nonzeros, dtype=c_int)
    nonzeros = np.zeros(num_nonzeros)
    
    c_matrix_idx = c_int(matrix_index)
    
    dll.getModelRelatedMatrix.argtypes = [
        POINTER(c_int),
        np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1)
    ]
    dll.getModelRelatedMatrix(byref(c_matrix_idx), row_ind, col_ind, nonzeros)
    
    # Convert 1-based indices to 0-based
    col_ind = col_ind - 1
    row_ind = row_ind - 1
    
    return csr_matrix((nonzeros, col_ind, row_ind), shape=(num_rows, num_cols))


def get_mass_matrix() -> csr_matrix:
    """Get global mass matrix M(q) at current configuration.

    The system must already be at the desired state via update_system() or
    because the solver just placed it there.

    Returns:
        Sparse mass matrix
    """
    info = _core.get_model_info()
    matrix_ids = np.array([MATRIX_TYPES["MASS"]], dtype=np.int32)
    row_pos = np.array([0], dtype=np.int32)
    col_pos = np.array([0], dtype=np.int32)
    scales = np.array([1.0])
    
    matrix_idx = create_matrix(matrix_ids, row_pos, col_pos, scales)
    return get_matrix(matrix_idx)


def get_stiffness_matrix() -> csr_matrix:
    """Get global stiffness matrix K at current configuration.

    The system must already be at the desired state via update_system() or
    because the solver just placed it there.

    Returns:
        Sparse stiffness matrix
    """
    matrix_ids = np.array([MATRIX_TYPES["STIFFNESS"]], dtype=np.int32)
    row_pos = np.array([0], dtype=np.int32)
    col_pos = np.array([0], dtype=np.int32)
    scales = np.array([1.0])
    
    matrix_idx = create_matrix(matrix_ids, row_pos, col_pos, scales)
    return get_matrix(matrix_idx)


def get_damping_matrix() -> csr_matrix:
    """Get global damping matrix D at current configuration.

    The system must already be at the desired state via update_system() or
    because the solver just placed it there.

    Returns:
        Sparse damping matrix
    """
    matrix_ids = np.array([MATRIX_TYPES["DAMPING"]], dtype=np.int32)
    row_pos = np.array([0], dtype=np.int32)
    col_pos = np.array([0], dtype=np.int32)
    scales = np.array([1.0])
    
    matrix_idx = create_matrix(matrix_ids, row_pos, col_pos, scales)
    return get_matrix(matrix_idx)

# ============================================================================
# Slots for optimization loops
# ============================================================================

class MBS_SysMat_slots:
    
    __slots__ = ['dll', 'dll_row_ind', 'dll_col_ind', 'dll_nonzeros', 
                 'modeMAT_sparse', 
                 'flat_idx', 'dense_mat_flat', 'dense_mat', 'sp_mat',
                 'c_idx_mat']
    
    
    def __init__(self, matrix_index: int, modeMAT_sparse):
        
        self.modeMAT_sparse = modeMAT_sparse
        
        self.dll = _core.get_dll()
        
        self.dll.getModelRelatedMatrix.argtypes = [POINTER(c_int),
                                                   np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
                                                   np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
                                                   np.ctypeslib.ndpointer(dtype=c_double, ndim=1)]
        
        mat_num_rows, mat_num_cols, num_nonzeros = get_matrix_dimensions(matrix_index)
        
        self.dll_row_ind = np.zeros(mat_num_rows + 1, dtype=c_int)
        self.dll_col_ind = np.zeros(num_nonzeros, dtype=c_int)
        self.dll_nonzeros = np.zeros(num_nonzeros)
        
        self.c_idx_mat = c_int(matrix_index)
        
        self.dll.getModelRelatedMatrix(byref(self.c_idx_mat), self.dll_row_ind, self.dll_col_ind, self.dll_nonzeros)
        
        # Convert 1-based indices to 0-based
        col_ind = self.dll_col_ind - 1
        row_ind = self.dll_row_ind - 1
        
        if self.modeMAT_sparse:
            self.sp_mat = csr_matrix((self.dll_nonzeros, col_ind, row_ind), shape=(mat_num_rows, mat_num_cols))
            
        else:
            # dense_mat[dense_mat_rows, col_ind] = dll_nonzeros
            dense_mat_rows = np.repeat(np.arange(mat_num_rows), np.diff(row_ind))
            
            """ Faster: Flat 1D index """
            self.flat_idx = dense_mat_rows * mat_num_cols + col_ind
            self.dense_mat = np.zeros((mat_num_rows, mat_num_cols))
            self.dense_mat_flat = self.dense_mat.ravel()

    def set_index(self, new_idx: int):
        self.c_idx_mat.value = new_idx
        
        
    def update_dll_nonzeros(self): 
        self.dll.getModelRelatedMatrix(byref(self.c_idx_mat), 
                                       self.dll_row_ind, 
                                       self.dll_col_ind, 
                                       self.dll_nonzeros)
        
        
    def update_data_in_matrix(self):
        if self.modeMAT_sparse:
            self.sp_mat.data[:] = self.dll_nonzeros
        else:
            self.dense_mat_flat[self.flat_idx] = self.dll_nonzeros