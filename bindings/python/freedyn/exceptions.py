"""
FreeDyn custom exceptions.

All FreeDyn-specific exceptions are defined here for easy exception handling.
"""


class FreeDynError(Exception):
    """Base exception for all FreeDyn errors."""
    pass


class DLLLoadError(FreeDynError):
    """Raised when the solver DLL (freedyn.dll) cannot be loaded."""
    pass


class ModelError(FreeDynError):
    """Raised when model operations fail."""
    pass


class SimulationError(FreeDynError):
    """Raised when simulation operations fail."""
    pass


class ParameterError(FreeDynError):
    """Raised when parameter modification fails."""
    pass


class MatrixError(FreeDynError):
    """Raised when matrix operations fail."""
    pass


class StateError(FreeDynError):
    """Raised when state operations fail."""
    pass


class ConstraintError(FreeDynError):
    """Raised when constraint-related operations fail."""
    pass
