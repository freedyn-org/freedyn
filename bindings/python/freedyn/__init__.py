"""
FreeDyn Python Bindings

Professional Python interface to FreeDyn multi-body dynamics simulator.

Quick Start:
    >>> import freedyn as fd
    >>> fd.initialize()
    >>> with fd.Model('model.fds') as model:
    ...     model.solve()
    ...     for time_idx, time, states in model.iterate_time_steps():
    ...         forces = fd.analysis.get_physical_dof_vector('SUMOFALLFORCES', time, states)

Main Classes:
    - Model: High-level interface for simulations
    - ModelInfo: Model information container

Functions:
    - initialize(): Load and initialize freedyn.dll (with legacy fallback)
    
Submodules:
    - analysis: Advanced analysis (matrices, vectors, Jacobians)
    - exceptions: Custom exception classes
"""

from ._version import __version__
from .models import Model, ModelInfo
from . import _core as core
from . import analysis
from .analysis import MBS_SysMat_slots
from . import exceptions

__author__ = "FreeDyn Team"

__all__ = [
    '__version__',
    'initialize',
    'Model',
    'ModelInfo',
    'core',
    'analysis',
    'exceptions',
]


def initialize(dll_path=None):
    """Initialize FreeDyn by loading freedyn.dll.
    
    Must be called before creating any models.
    
    Args:
        dll_path: Optional path to the solver DLL. If None, searches standard
            locations for freedyn.dll, then falls back to FDCI_Dll.dll for
            compatibility.
        
    Raises:
        DLLLoadError: If the DLL cannot be found or loaded.
    """
    core.initialize(dll_path)
