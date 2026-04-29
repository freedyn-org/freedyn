"""Reusable vector and dense derivative buffers for high-frequency C-interface retrieval."""

from ctypes import c_int, c_double, c_char_p, byref, POINTER

import numpy as np

from . import _core
from .exceptions import ConstraintError, ParameterError


class ModelVectorBuffer:
    """Base class for reusable DLL-backed vector buffers.

    Args:
        vector_symbol: C-interface vector identifier string.
        vector_length: Length of the target vector.
        dll_function_name: Name of the DLL function used to fill the vector.
    """

    __slots__ = [
        "dll",
        "c_vector_type",
        "data",
        "c_success",
        "dll_function",
        "vector_label",
    ]

    def __init__(self, vector_symbol: str, vector_length: int, dll_function_name: str):
        self.dll = _core.get_dll()
        self.vector_label = vector_symbol
        self.c_vector_type = c_char_p(vector_symbol.encode("utf-8"))
        self.data = np.zeros((vector_length, 1), dtype=c_double)
        self.c_success = c_int(-1)

        self.dll_function = getattr(self.dll, dll_function_name)
        self.dll_function.argtypes = [
            c_char_p,
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            POINTER(c_int),
        ]

    def update_from_dll(self) -> None:
        """Refresh vector values in-place from the DLL."""
        self.dll_function(self.c_vector_type, self.data, byref(self.c_success))
        if self.c_success.value <= 0:
            raise ConstraintError(f"Failed to compute vector {self.vector_label}")


class ForceVectorBuffer(ModelVectorBuffer):
    """Reusable buffer for force/dynamics vectors over generalized coordinates."""

    __slots__ = ()

    def __init__(self, vector_symbol: str):
        info = _core.get_model_info()
        super().__init__(
            vector_symbol=vector_symbol,
            vector_length=info["numGeneralizedCoordinates"],
            dll_function_name="getForceVector",
        )


class ConstraintVectorBuffer(ModelVectorBuffer):
    """Reusable buffer for constraint-related vectors over Lagrange multipliers."""

    __slots__ = ()

    def __init__(self, vector_symbol: str):
        info = _core.get_model_info()
        super().__init__(
            vector_symbol=vector_symbol,
            vector_length=info["numLagrangeMultipliers"],
            dll_function_name="getConstraintVector",
        )


class ForceParameterDerivativeMatrixBuffer:
    """Reusable dense matrix buffer for dQext/d(param) columns.

    Each requested parameter label is validated once against the active model.
    The buffer then reuses one preallocated dense matrix with one column per
    parameter label.

    Args:
        parameter_labels: Ordered iterable of parameter labels.

    Raises:
        ParameterError: If no labels are provided or a label does not exist.
    """

    # Keep this class dict-backed. A slots-based layout showed unstable behavior
    # in some Python 3.13 + ctypes runs when creating this buffer repeatedly.

    def __init__(self, parameter_labels, validate_labels: bool = True, num_rows: int | None = None):
        labels = list(parameter_labels)
        if not labels:
            raise ParameterError("At least one parameter label is required")

        if validate_labels:
            available = set(_core.get_parameter_names())
            missing = [label for label in labels if label not in available]
            if missing:
                missing_text = ", ".join(missing)
                raise ParameterError(f"Unknown parameter label(s): {missing_text}")

        if num_rows is None:
            info = _core.get_model_info()
            self.num_rows = info["numGeneralizedCoordinates"]
        else:
            self.num_rows = int(num_rows)
        self.dll = _core.get_dll()
        self.parameter_labels = labels
        self.data = np.zeros((self.num_rows, len(labels)), dtype=c_double)
        self.c_success = c_int(-1)

        self.dll.getForceVector.argtypes = [
            c_char_p,
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            POINTER(c_int),
        ]

    def update_from_dll(self) -> None:
        """Refresh all parameter-derivative columns in-place from the DLL."""
        for column_index, label in enumerate(self.parameter_labels):
            c_label = c_char_p(label.encode("utf-8"))
            column_view = self.data[:, column_index:column_index + 1]
            self.dll.getForceVector(c_label, column_view, byref(self.c_success))
            if self.c_success.value <= 0:
                raise ParameterError(f"Failed to compute force derivative for parameter {label}")
