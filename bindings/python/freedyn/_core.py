"""
FreeDyn Low-Level C Interface Bindings

Direct bindings to the FreeDyn solver DLL (freedyn.dll). For most use cases,
use the higher-level API in models.py instead.

Internal module - not meant for direct use by end users.
"""

from ctypes import CDLL, Structure, c_int, c_double, c_char, c_char_p, create_string_buffer, byref, POINTER
from typing import Optional, Dict
import numpy as np
import os

from .exceptions import DLLLoadError, ModelError, SimulationError, ParameterError, StateError
from ._ctypes_utils import encode_string, decode_string, check_success, create_error_buffer


DEFAULT_DLL_NAMES = ("freedyn.dll", "FDCI_Dll.dll")


# Global DLL instance
_dll: Optional[CDLL] = None


class ModelInfo(Structure):
    """C structure matching FreeDyn's model information struct."""
    _fields_ = [
        ('numAllDofs', c_int),
        ('numPhyDofs', c_int),
        ('numIntDof', c_int),
        ('numExtDof', c_int),
        ('numBodies', c_int),
        ('numExtConstr', c_int),
        ('numForces', c_int),
        ('numMeasures', c_int)
    ]


def _resolve_symbol(dll: CDLL, *names: str):
    """Resolve first available symbol name from the DLL."""
    for name in names:
        if hasattr(dll, name):
            return getattr(dll, name)
    raise AttributeError(f"None of these symbols found: {', '.join(names)}")


def initialize(dll_path: Optional[str] = None) -> None:
    """Initialize FreeDyn API by loading the solver DLL (freedyn.dll).
    
    Args:
        dll_path: Optional path to the DLL. If None, searches for freedyn.dll
            (preferred) then FDCI_Dll.dll for backwards compatibility.
        
    Raises:
        DLLLoadError: If DLL cannot be found or loaded.
    """
    global _dll

    errors = []

    def try_load(path: str) -> Optional[CDLL]:
        try:
            return CDLL(path)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            return None

    candidates = []

    if dll_path is not None:
        candidates.append(dll_path)
    else:
        # Search locations:
        #   1) package bin/  (inside installed wheel)
        #   2) top-level bin/x64_MD/  (repo / extracted release)
        #   3) PATH
        package_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin'))
        repo_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bin', 'x64_MD'))

        search_dirs = [d for d in (package_bin, repo_bin) if os.path.isdir(d)]

        for bin_dir in search_dirs:
            current_path = os.environ.get('PATH', '')
            if bin_dir not in current_path:
                os.environ['PATH'] = f"{bin_dir};{current_path}"

            for name in DEFAULT_DLL_NAMES:
                candidate = os.path.join(bin_dir, name)
                if os.path.exists(candidate):
                    candidates.append(candidate)

        # Fallback to PATH resolution
        candidates.extend(DEFAULT_DLL_NAMES)

    for candidate in candidates:
        dll = try_load(candidate)
        if dll is not None:
            _dll = dll
            return

    tried = "; ".join(candidates) if candidates else "<none>"
    detail = " | ".join(errors) if errors else "Unknown error"
    raise DLLLoadError(
        f"Failed to load FreeDyn DLL. Tried: {tried}. Details: {detail}"
    )


def get_dll() -> CDLL:
    """Get the loaded DLL instance.
    
    Returns:
        CDLL object
        
    Raises:
        DLLLoadError: If DLL is not loaded
    """
    if _dll is None:
        raise DLLLoadError("DLL not initialized. Call initialize() first.")
    return _dll


# ============================================================================
# Model Management
# ============================================================================

def create_model(fds_file_path: str, status_output: str = 'SCREEN') -> int:
    """Create a FreeDyn model from .fds file.
    
    Args:
        fds_file_path: Path to .fds model file
        status_output: Output mode: 'NO', 'FILE', 'SCREEN', or 'SCREENANDFILE'
        
    Returns:
        Model index (integer ID)
        
    Raises:
        ModelError: If model creation fails
    """
    dll = get_dll()

    abs_fds_path = os.path.abspath(fds_file_path)
    c_path = encode_string(abs_fds_path)
    c_status = encode_string(status_output)
    c_model_idx = c_int(-1)
    error_buf, get_error = create_error_buffer()

    dll.createFreeDynModel.argtypes = [c_char_p, c_char_p, POINTER(c_int), POINTER(c_char)]

    # Some models reference additional files via relative paths.
    # Resolve these against the .fds parent directory during model creation.
    prev_cwd = os.getcwd()
    model_dir = os.path.dirname(abs_fds_path)
    try:
        if model_dir:
            os.chdir(model_dir)
        dll.createFreeDynModel(c_path, c_status, byref(c_model_idx), error_buf)
    finally:
        os.chdir(prev_cwd)
    
    if c_model_idx.value < 0:
        raise ModelError(f"Failed to create model from {abs_fds_path}: {get_error()}")
    
    return c_model_idx.value


def delete_model(model_index: int) -> None:
    """Delete a FreeDyn model and clean up resources.
    
    Args:
        model_index: Model index to delete
        
    Raises:
        ModelError: If deletion fails
    """
    dll = get_dll()
    
    c_model_idx = c_int(model_index)
    c_success = c_int(-1)
    
    dll.deleteFreeDynModel(byref(c_model_idx), byref(c_success))
    
    check_success(c_success.value, f"Delete model {model_index}", exception_class=ModelError)


def set_model_active(model_index: int) -> None:
    """Set a model as active for simulation.
    
    Args:
        model_index: Model index to activate
        
    Raises:
        ModelError: If activation fails
    """
    dll = get_dll()
    
    c_model_idx = c_int(model_index)
    c_success = c_int(-1)
    
    try:
        set_active = _resolve_symbol(dll, "setModelAsActive", "setModelAsActiv")
    except AttributeError as exc:
        raise ModelError(str(exc)) from exc

    set_active.argtypes = [POINTER(c_int), POINTER(c_int)]
    set_active(byref(c_model_idx), byref(c_success))
    
    check_success(c_success.value, f"Set model {model_index} active", exception_class=ModelError)


# ============================================================================
# Model Information
# ============================================================================

def get_model_info() -> Dict[str, int]:
    """Get model information.
    
    Returns:
        Dictionary with keys: numAllDofs, numPhyDofs, numIntDof, numExtDof,
                            numBodies, numExtConstr, numForces, numMeasures
    """
    dll = get_dll()
    
    # New API (2026+): getModelDofInfo
    if hasattr(dll, "getModelDofInfo"):
        n_q = c_int(0)
        n_l = c_int(0)
        n_body_states = c_int(0)
        n_bodies = c_int(0)
        n_ext_constr = c_int(0)
        n_forces = c_int(0)
        n_measures = c_int(0)
        c_success = c_int(-1)

        dll.getModelDofInfo.argtypes = [
            POINTER(c_int), POINTER(c_int), POINTER(c_int),
            POINTER(c_int), POINTER(c_int), POINTER(c_int),
            POINTER(c_int), POINTER(c_int)
        ]
        dll.getModelDofInfo(
            byref(n_q), byref(n_l), byref(n_body_states),
            byref(n_bodies), byref(n_ext_constr), byref(n_forces),
            byref(n_measures), byref(c_success)
        )
        check_success(c_success.value, "Get model DOF info", exception_class=ModelError)

        return {
            # New keys
            "numGeneralizedCoordinates": n_q.value,
            "numLagrangeMultipliers": n_l.value,
            "numBodyStates": n_body_states.value,
            "numBodies": n_bodies.value,
            "numExtConstraints": n_ext_constr.value,
            "numForces": n_forces.value,
            "numMeasures": n_measures.value,
            # Backward-compatible keys expected by current high-level code
            "numAllDofs": n_q.value + n_l.value,
            "numPhyDofs": n_q.value,
            "numIntDof": 0,
            "numExtDof": n_l.value,
            "numExtConstr": n_ext_constr.value,
        }

    # Legacy API fallback
    model_info = ModelInfo()
    if not hasattr(dll, "getModelInfoStruct"):
        raise ModelError("Neither getModelDofInfo nor getModelInfoStruct is available in DLL")

    dll.getModelInfoStruct.argtypes = [POINTER(ModelInfo)]
    dll.getModelInfoStruct(model_info)

    return {
        "numAllDofs": model_info.numAllDofs,
        "numPhyDofs": model_info.numPhyDofs,
        "numIntDof": model_info.numIntDof,
        "numExtDof": model_info.numExtDof,
        "numBodies": model_info.numBodies,
        "numExtConstr": model_info.numExtConstr,
        "numExtConstraints": model_info.numExtConstr,
        "numForces": model_info.numForces,
        "numMeasures": model_info.numMeasures,
        "numGeneralizedCoordinates": model_info.numPhyDofs,
        "numLagrangeMultipliers": model_info.numIntDof + model_info.numExtDof,
        "numBodyStates": model_info.numPhyDofs,
    }


# ============================================================================
# Simulation
# ============================================================================

def solve_equations_of_motion() -> None:
    """Solve equations of motion for entire time period defined in model.
    
    Raises:
        SimulationError: If solving fails
    """
    dll = get_dll()
    
    c_success = c_int(-1)
    dll.solveEoM(byref(c_success))
    
    check_success(c_success.value, "Solve equations of motion", exception_class=SimulationError)


def solve_time_interval(end_time: float) -> None:
    """Solve simulation for a time interval.
    
    Args:
        end_time: End time of interval
        
    Raises:
        SimulationError: If solving fails
    """
    dll = get_dll()
    
    c_time = c_double(end_time)
    c_success = c_int(-1)
    
    dll.solveTimeInterval(byref(c_time), byref(c_success))
    
    check_success(c_success.value, f"Solve time interval to t={end_time}", exception_class=SimulationError)


def compute_initial_conditions() -> None:
    """Compute initial conditions for the model.
    
    Raises:
        SimulationError: If computation fails
    """
    dll = get_dll()
    
    c_success = c_int(-1)
    dll.computeInitialConditions(byref(c_success))
    
    check_success(c_success.value, "Compute initial conditions", exception_class=SimulationError)


def get_num_time_steps() -> int:
    """Get number of time steps from last simulation.
    
    Returns:
        Number of time steps
    """
    dll = get_dll()
    
    c_num_steps = c_int(-1)

    # New API signature includes oSuccess
    if hasattr(dll, "getNumberOfSolutionTimeSteps"):
        c_success = c_int(-1)
        dll.getNumberOfSolutionTimeSteps.argtypes = [POINTER(c_int), POINTER(c_int)]
        try:
            dll.getNumberOfSolutionTimeSteps(byref(c_num_steps), byref(c_success))
            check_success(c_success.value, "Get number of solution time steps", exception_class=SimulationError)
            return c_num_steps.value
        except TypeError:
            # Fallback for legacy one-argument signature
            pass

    dll.getNumberOfSolutionTimeSteps.argtypes = [POINTER(c_int)]
    dll.getNumberOfSolutionTimeSteps(byref(c_num_steps))
    return c_num_steps.value


# ============================================================================
# States and Results
# ============================================================================

def get_states_at_time_index(time_index: int, states: Dict[str, np.ndarray]) -> float:
    """Get states at specific time index from simulation results.
    
    Args:
        time_index: Time step index (0-based)
        states: State dict to be updated with Q, Qd, Qdd values
        
    Returns:
        Time value at index
        
    Raises:
        StateError: If retrieval fails
    """
    dll = get_dll()
    
    c_time_idx = c_int(time_index + 1)  # C interface uses 1-based indexing
    c_time = c_double(0.0)

    # New API: get generalized states and keep only Q in provided container
    if hasattr(dll, "getGeneralizedStatesAtTimeIndex"):
        info = get_model_info()
        qd = np.zeros_like(states["Q"])
        qdd = np.zeros_like(states["Q"])
        l = np.zeros((info["numLagrangeMultipliers"], 1), dtype=c_double)
        c_success = c_int(-1)

        dll.getGeneralizedStatesAtTimeIndex.argtypes = [
            POINTER(c_int), POINTER(c_double),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            POINTER(c_int)
        ]
        dll.getGeneralizedStatesAtTimeIndex(
            byref(c_time_idx), byref(c_time),
            states["Q"], qd, qdd, l, byref(c_success)
        )
        check_success(c_success.value, f"Get states at time index {time_index}", exception_class=StateError)
        return c_time.value

    # Legacy API fallback
    dll.getStatesViaTimeIndexOfSolverResult.argtypes = [
        POINTER(c_int),
        POINTER(c_double),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2)
    ]
    dll.getStatesViaTimeIndexOfSolverResult(byref(c_time_idx), byref(c_time), states["Q"])
    return c_time.value


def get_states_at_time_index_full(time_index: int, states: Dict[str, np.ndarray]) -> float:
    """Get full states (Q, Qd, Qdd, L) at specific time index.
    
    Args:
        time_index: Time step index (0-based)
        states: State dict to be updated
        
    Returns:
        Time value at index
        
    Raises:
        StateError: If retrieval fails
    """
    dll = get_dll()
    
    c_time_idx = c_int(time_index + 1)
    c_time = c_double(0.0)

    if hasattr(dll, "getGeneralizedStatesAtTimeIndex"):
        c_success = c_int(-1)
        dll.getGeneralizedStatesAtTimeIndex.argtypes = [
            POINTER(c_int), POINTER(c_double),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
            POINTER(c_int)
        ]
        dll.getGeneralizedStatesAtTimeIndex(
            byref(c_time_idx), byref(c_time),
            states["Q"], states["Qd"], states["Qdd"], states["L"],
            byref(c_success)
        )
        check_success(c_success.value, f"Get full states at time index {time_index}", exception_class=StateError)
        return c_time.value

    # Legacy fallback
    dll.getStatesViaTimeIndexOfSolverResult2.argtypes = [
        POINTER(c_int),
        POINTER(c_double),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2)
    ]
    dll.getStatesViaTimeIndexOfSolverResult2(
        byref(c_time_idx), byref(c_time),
        states["Q"], states["Qd"], states["Qdd"], states["L"]
    )
    return c_time.value


def update_system(time: float, states: Dict[str, np.ndarray]) -> None:
    """Update system to a specific time with given states.
    
    Args:
        time: Time value
        states: State dictionary with Q, Qd, Qdd, L
        
    Raises:
        StateError: If update fails
    """
    dll = get_dll()
    
    c_time = c_double(time)
    c_success = c_int(-1)
    
    dll.updateSystem.argtypes = [
        POINTER(c_double),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=2),
        POINTER(c_int)
    ]
    dll.updateSystem(
        byref(c_time),
        states["Q"], states["Qd"], states["Qdd"], states["L"],
        byref(c_success)
    )
    
    check_success(c_success.value, f"Update system to t={time}", exception_class=StateError)


# ============================================================================
# Parameters and Measures
# ============================================================================

def modify_parameter(param_label: str, param_value: float) -> None:
    """Modify a model parameter.
    
    Args:
        param_label: Name of parameter
        param_value: New parameter value
        
    Raises:
        ParameterError: If modification fails
    """
    dll = get_dll()
    
    c_success = c_int(-1)
    c_job_flag = c_int(2)  # modify mode
    c_label = encode_string(param_label)
    c_value = c_double(param_value)
    c_dummy = c_int(0)
    c_empty_array = np.array([], dtype=c_double)
    
    dll.modifyDataObject.argtypes = [
        c_char_p,
        POINTER(c_int),
        POINTER(c_double),
        POINTER(c_int),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        POINTER(c_int)
    ]
    dll.modifyDataObject(
        c_label, byref(c_job_flag), byref(c_value), byref(c_dummy),
        c_empty_array, c_empty_array, byref(c_success)
    )
    
    check_success(c_success.value, f"Modify parameter {param_label}", exception_class=ParameterError)


def modify_spline(spline_label: str, spline_data: np.ndarray) -> None:
    """Modify a spline in the model.
    
    Args:
        spline_label: Name of spline
        spline_data: 2D numpy array with columns [x_values, y_values]
        
    Raises:
        ParameterError: If modification fails
    """
    dll = get_dll()
    
    c_success = c_int(-1)
    c_job_flag = c_int(1)  # spline mode
    c_num_data = c_int(spline_data.shape[0])
    c_label = encode_string(spline_label)
    c_dummy = c_double(0.0)
    
    dll.modifyDataObject.argtypes = [
        c_char_p,
        POINTER(c_int),
        POINTER(c_double),
        POINTER(c_int),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
        POINTER(c_int)
    ]
    dll.modifyDataObject(
        c_label, byref(c_job_flag), c_dummy, byref(c_num_data),
        spline_data[:, 0], spline_data[:, 1], byref(c_success)
    )
    
    check_success(c_success.value, f"Modify spline {spline_label}", exception_class=ParameterError)


def get_measure_value(measure_label: str) -> float:
    """Get current value of a measure.
    
    Args:
        measure_label: Name of the measure
        
    Returns:
        Float value of measure
        
    Raises:
        ParameterError: If measure not found
    """
    dll = get_dll()
    
    c_success = c_int(-1)
    c_label = encode_string(measure_label)
    c_value = c_double(0.0)
    
    dll.getMeasureValueWithMeasureName.argtypes = [
        c_char_p,
        POINTER(c_double),
        POINTER(c_int)
    ]
    dll.getMeasureValueWithMeasureName(c_label, byref(c_value), byref(c_success))
    
    check_success(c_success.value, f"Get measure {measure_label}", exception_class=ParameterError)
    
    return c_value.value


def get_measure_names() -> list:
    """Get all available measure names in model.
    
    Returns:
        List of measure name strings
    """
    dll = get_dll()
    
    model_info = get_model_info()
    measure_names = []
    
    for i in range(model_info["numMeasures"]):
        c_index = c_int(i)
        c_job_flag = c_int(1)
        c_name_buf = create_string_buffer(512)
        int_info = np.zeros(1, dtype=c_int)
        double_info = np.zeros(1, dtype=c_double)

        dll.getMeasureInformation.argtypes = [
            POINTER(c_int), POINTER(c_int),
            np.ctypeslib.ndpointer(dtype=c_int, ndim=1),
            np.ctypeslib.ndpointer(dtype=c_double, ndim=1),
            POINTER(c_char)
        ]
        dll.getMeasureInformation(byref(c_index), byref(c_job_flag), int_info, double_info, c_name_buf)
        measure_names.append(decode_string(c_name_buf.value))
    
    return measure_names


# ============================================================================
# Deprecated: Old API (for backwards compatibility)
# ============================================================================

# Keep the old function names for backwards compatibility
def init(dll_path: Optional[str] = None) -> None:
    """Deprecated: Use initialize() instead."""
    initialize(dll_path)


# Make the old fdci_dll global accessible (deprecated)
@property
def fdci_dll():
    """Deprecated: For backwards compatibility only."""
    return get_dll()
