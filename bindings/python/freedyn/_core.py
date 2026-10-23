"""
FreeDyn Low-Level C Interface Bindings

Direct bindings to the FreeDyn solver DLL (freedyn.dll). For most use cases,
use the higher-level API in models.py instead.

Internal module - not meant for direct use by end users.
"""

from ctypes import CDLL, c_int, c_double, c_char, c_char_p, create_string_buffer, byref, POINTER
from typing import Optional, Dict
import numpy as np
import os

from .exceptions import DLLLoadError, ModelError, SimulationError, ParameterError, StateError
from ._ctypes_utils import encode_string, decode_string, check_success, create_error_buffer, as_ptr


DEFAULT_DLL_NAMES = ("freedyn.dll",)
DEFAULT_DLL_NAMES_MT = ("freedyn_mt.dll",)

# The DLL writes a fixed 512-character field for labels and messages,
# regardless of the minimum length stated in the header.
CHAR_FIELD_LENGTH = 512


# Global DLL instance
_dll: Optional[CDLL] = None

_P_INT = POINTER(c_int)
_P_DOUBLE = POINTER(c_double)
_P_CHAR = POINTER(c_char)

# argtypes of every C-API function, declared once when the DLL is loaded.
# ctypes shares one function object per name, so argtypes must never be set
# anywhere else: a second, different declaration silently breaks all other
# callers. Arrays are passed as plain pointers (see _ctypes_utils.as_ptr).
_SIGNATURES = {
    "createFreeDynModel": [c_char_p, c_char_p, _P_INT, _P_CHAR],
    "setModelAsActive": [_P_INT, _P_INT],
    "deleteFreeDynModel": [_P_INT, _P_INT],
    "resetActiveModelForRerun": [_P_INT],
    "getModelDofInfo": [_P_INT] * 8,
    "solveEoM": [_P_INT],
    "solveTimeInterval": [_P_DOUBLE, _P_INT],
    "computeInitialConditions": [_P_INT],
    "getNumberOfSolutionTimeSteps": [_P_INT, _P_INT],
    "getTime": [_P_INT, _P_DOUBLE, _P_INT],
    "getGeneralizedStatesAtTimeIndex": [_P_INT, _P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_INT],
    "updateSystem": [_P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_DOUBLE, _P_INT],
    "updateSystemAtTimeIndex": [_P_INT, _P_INT],
    "updateJacobian": [_P_INT],
    "modifyDataObject": [c_char_p, _P_INT, _P_DOUBLE, _P_INT, _P_DOUBLE, _P_DOUBLE, _P_INT],
    "getParameterInformation": [_P_INT, _P_INT, _P_INT, _P_DOUBLE, _P_CHAR],
    "getMeasureInformation": [_P_INT, _P_INT, _P_INT, _P_DOUBLE, _P_CHAR],
    "getMeasureValueWithMeasureName": [c_char_p, _P_DOUBLE, _P_INT],
    "getMeasureDerivative": [c_char_p, _P_DOUBLE, _P_INT],
    "getMeasureDerivativeQd": [c_char_p, _P_DOUBLE, _P_INT],
    "getForceVector": [c_char_p, _P_DOUBLE, _P_INT],
    "getConstraintVector": [c_char_p, _P_DOUBLE, _P_INT],
    "createModelRelatedMatrix": [_P_INT, _P_INT, _P_INT, _P_INT, _P_INT, _P_INT, _P_DOUBLE, _P_INT],
    "getDimOfModelRelatedMatrix": [_P_INT, _P_INT, _P_INT, _P_INT],
    "getModelRelatedMatrix": [_P_INT, _P_INT, _P_INT, _P_DOUBLE],
}


def _declare_signatures(dll: CDLL) -> None:
    """Set argtypes for all known C-API functions; optional ones may be missing."""
    for name, argtypes in _SIGNATURES.items():
        if hasattr(dll, name):
            getattr(dll, name).argtypes = argtypes



def initialize(dll_path: Optional[str] = None) -> None:
    """Initialize FreeDyn API by loading the solver DLL (freedyn.dll).
    
    Args:
        dll_path: Optional path to the DLL. If None, searches for freedyn.dll
            in the package bin directory, then falls back to PATH resolution.
        
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
        #   default:     package bin/  — MD DLLs via editable/wheel install
        #   MD override: top-level bin/x64_MD/ first, then package bin/ as fallback
        #   MT override: top-level bin/x64_MT/ first, then package bin/ as fallback
        #   always:      PATH fallback (bare DLL names)
        package_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin'))
        repo_bin_md = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bin', 'x64_MD')
        )
        repo_bin_mt = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bin', 'x64_MT')
        )

        runtime = os.environ.get("FREEDYN_RUNTIME", "").upper()

        if runtime == "MT":
            search_dirs = [d for d in (repo_bin_mt, package_bin) if os.path.isdir(d)]
            dll_names = DEFAULT_DLL_NAMES_MT
        elif runtime == "MD":
            search_dirs = [d for d in (repo_bin_md, package_bin) if os.path.isdir(d)]
            dll_names = DEFAULT_DLL_NAMES
        else:
            search_dirs = [d for d in (package_bin,) if os.path.isdir(d)]
            dll_names = DEFAULT_DLL_NAMES

        for bin_dir in search_dirs:
            current_path = os.environ.get('PATH', '')
            if bin_dir not in current_path:
                os.environ['PATH'] = f"{bin_dir};{current_path}"

            for name in dll_names:
                candidate = os.path.join(bin_dir, name)
                if os.path.exists(candidate):
                    candidates.append(candidate)

        # Fallback to PATH resolution
        candidates.extend(DEFAULT_DLL_NAMES)

    for candidate in candidates:
        dll = try_load(candidate)
        if dll is not None:
            _declare_signatures(dll)
            _dll = dll
            return

    tried = "; ".join(candidates) if candidates else "<none>"
    detail = " | ".join(errors) if errors else "Unknown error"
    raise DLLLoadError(
        "Failed to load FreeDyn DLL. "
        f"Tried: {tried}. Details: {detail}. "
        "Ensure freedyn.dll and all dependent DLLs are present and match your Python/package build."
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
    error_buf, get_error = create_error_buffer(CHAR_FIELD_LENGTH)

    # Some models reference additional files via relative paths.
    # Resolve these against the .fds parent directory during model creation.
    prev_cwd = os.getcwd()
    model_dir = os.path.dirname(abs_fds_path)
    try:
        if model_dir:
            os.chdir(model_dir)
        try:
            dll.createFreeDynModel(c_path, c_status, byref(c_model_idx), error_buf)
        except OSError as exc:
            raise ModelError(
                f"Native model creation crashed for {abs_fds_path}: {exc}. "
                "Check DLL compatibility and model-dependent input files."
            ) from exc
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
    
    dll.setModelAsActive(byref(c_model_idx), byref(c_success))
    
    check_success(c_success.value, f"Set model {model_index} active", exception_class=ModelError)


def reset_active_model_for_rerun() -> None:
    """Reset the active model for a clean rerun after data changes.

    Raises:
        ModelError: If the DLL does not support this operation or it fails
    """
    dll = get_dll()

    if not hasattr(dll, "resetActiveModelForRerun"):
        raise ModelError("resetActiveModelForRerun is not available in DLL")

    c_success = c_int(-1)
    dll.resetActiveModelForRerun(byref(c_success))

    check_success(c_success.value, "Reset active model for rerun", exception_class=ModelError)


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

    n_q = c_int(0)
    n_l = c_int(0)
    n_body_states = c_int(0)
    n_bodies = c_int(0)
    n_ext_constr = c_int(0)
    n_forces = c_int(0)
    n_measures = c_int(0)
    c_success = c_int(-1)

    dll.getModelDofInfo(
        byref(n_q), byref(n_l), byref(n_body_states),
        byref(n_bodies), byref(n_ext_constr), byref(n_forces),
        byref(n_measures), byref(c_success)
    )
    check_success(c_success.value, "Get model DOF info", exception_class=ModelError)

    return {
        "numGeneralizedCoordinates": n_q.value,
        "numLagrangeMultipliers": n_l.value,
        "numBodyStates": n_body_states.value,
        "numBodies": n_bodies.value,
        "numExtConstraints": n_ext_constr.value,
        "numForces": n_forces.value,
        "numMeasures": n_measures.value,
        "numAllDofs": n_q.value + n_l.value,
        "numPhyDofs": n_q.value,
        "numIntDof": 0,
        "numExtDof": n_l.value,
        "numExtConstr": n_ext_constr.value,
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
    c_success = c_int(-1)
    dll.getNumberOfSolutionTimeSteps(byref(c_num_steps), byref(c_success))
    check_success(c_success.value, "Get number of solution time steps", exception_class=SimulationError)
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
    info = get_model_info()
    n_q = info["numGeneralizedCoordinates"]
    qd = np.zeros((n_q, 1), dtype=c_double)
    qdd = np.zeros((n_q, 1), dtype=c_double)
    l = np.zeros((info["numLagrangeMultipliers"], 1), dtype=c_double)

    return get_states_at_time_index_ptr(
        time_index,
        as_ptr(states["Q"], c_double, n_q),
        as_ptr(qd, c_double), as_ptr(qdd, c_double), as_ptr(l, c_double),
    )


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
    info = get_model_info()
    n_q = info["numGeneralizedCoordinates"]
    n_l = info["numLagrangeMultipliers"]

    return get_states_at_time_index_ptr(
        time_index,
        as_ptr(states["Q"], c_double, n_q),
        as_ptr(states["Qd"], c_double, n_q),
        as_ptr(states["Qdd"], c_double, n_q),
        as_ptr(states["L"], c_double, n_l),
    )


def get_states_at_time_index_ptr(time_index: int, p_q, p_qd, p_qdd, p_l) -> float:
    """Get full states at a time index into caller-owned buffers given as pointers.

    Fast path for loops: create the pointers once with _ctypes_utils.as_ptr
    and reuse them for every call.

    Args:
        time_index: Time step index (0-based)
        p_q, p_qd, p_qdd: POINTER(c_double) to buffers of numGeneralizedCoordinates
        p_l: POINTER(c_double) to a buffer of numLagrangeMultipliers

    Returns:
        Time value at index

    Raises:
        StateError: If retrieval fails
    """
    dll = get_dll()

    c_time_idx = c_int(time_index + 1)  # C interface uses 1-based indexing
    c_time = c_double(0.0)
    c_success = c_int(-1)

    dll.getGeneralizedStatesAtTimeIndex(
        byref(c_time_idx), byref(c_time),
        p_q, p_qd, p_qdd, p_l,
        byref(c_success)
    )
    check_success(c_success.value, f"Get full states at time index {time_index}", exception_class=StateError)
    return c_time.value


def get_time_at_index(time_index: int) -> float:
    """Get only the simulation time value at a specific solver-result index.

    Args:
        time_index: Time step index (0-based)

    Returns:
        Time value at index

    Raises:
        StateError: If retrieval fails
    """
    dll = get_dll()

    c_time_idx = c_int(time_index + 1)
    c_time = c_double(0.0)
    c_success = c_int(-1)

    dll.getTime(byref(c_time_idx), byref(c_time), byref(c_success))
    check_success(c_success.value, f"Get time at index {time_index}", exception_class=StateError)
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
    
    dll.updateSystem(
        byref(c_time),
        as_ptr(states["Q"], c_double), as_ptr(states["Qd"], c_double),
        as_ptr(states["Qdd"], c_double), as_ptr(states["L"], c_double),
        byref(c_success)
    )
    
    check_success(c_success.value, f"Update system to t={time}", exception_class=StateError)


def update_system_at_time_index(time_index: int) -> None:
    """Restore solver state at a stored time index into the cached system state.

    Args:
        time_index: Time step index (0-based)

    Raises:
        StateError: If restoration fails
    """
    dll = get_dll()

    c_time_idx = c_int(time_index + 1)
    c_success = c_int(-1)
    dll.updateSystemAtTimeIndex(byref(c_time_idx), byref(c_success))
    check_success(c_success.value, f"Update system at time index {time_index}", exception_class=StateError)


def update_jacobian() -> None:
    """Recompute Jacobian matrices at the current cached system state.

    Uses the state/time cached by the most recent successful call to
    update_system() or update_system_at_time_index(). Does not alter
    the cached state.

    Raises:
        StateError: If the DLL does not support this operation or it fails.
    """
    dll = get_dll()

    if not hasattr(dll, "updateJacobian"):
        raise StateError("updateJacobian is not available in DLL")

    c_success = c_int(-1)
    dll.updateJacobian(byref(c_success))

    check_success(c_success.value, "Update Jacobian", exception_class=StateError)


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
    
    p_empty = as_ptr(c_empty_array, c_double)
    dll.modifyDataObject(
        c_label, byref(c_job_flag), byref(c_value), byref(c_dummy),
        p_empty, p_empty, byref(c_success)
    )
    
    check_success(c_success.value, f"Modify parameter {param_label}", exception_class=ParameterError)


def get_parameter_names() -> list:
    """Get all parameter names exposed by the active model.

    Returns:
        List of parameter name strings

    Raises:
        ParameterError: If the DLL does not support parameter introspection
    """
    dll = get_dll()

    if not hasattr(dll, "getParameterInformation"):
        raise ParameterError("getParameterInformation is not available in DLL")

    c_job_flag = c_int(2)
    int_infos = np.zeros(1, dtype=c_int)
    double_infos = np.zeros(1, dtype=c_double)
    p_int_infos = as_ptr(int_infos, c_int)
    p_double_infos = as_ptr(double_infos, c_double)
    char_infos = create_string_buffer(CHAR_FIELD_LENGTH)

    # Parameters use one-based label indices.
    c_param_idx = c_int(1)
    dll.getParameterInformation(
        byref(c_param_idx),
        byref(c_job_flag),
        p_int_infos,
        p_double_infos,
        char_infos
    )
    param_count = int(int_infos[0])

    if param_count <= 0:
        return []

    c_job_flag = c_int(1)

    def _read_name(index: int) -> str:
        int_infos.fill(0)
        double_infos.fill(0.0)
        name_buf = create_string_buffer(CHAR_FIELD_LENGTH)
        c_param_idx_local = c_int(index)
        dll.getParameterInformation(
            byref(c_param_idx_local),
            byref(c_job_flag),
            p_int_infos,
            p_double_infos,
            name_buf
        )
        return decode_string(name_buf.value).strip()

    return [_read_name(1 + offset) for offset in range(param_count)]


def modify_spline(spline_label: str, spline_data: np.ndarray) -> None:
    """Modify a spline in the model.
    
    Args:
        spline_label: Name of spline
        spline_data: 2D numpy array with columns [x_values, y_values]
        
    Raises:
        ParameterError: If modification fails
    """
    dll = get_dll()
    
    spline_arr = np.asarray(spline_data, dtype=c_double)
    if spline_arr.ndim != 2 or spline_arr.shape[1] != 2:
        raise ParameterError("spline_data must be a 2D array with exactly 2 columns: [x_values, y_values]")

    # Column slices from C-ordered 2D arrays are strided and not contiguous.
    # The C API expects contiguous 1D buffers for iDataX/iDataY.
    x_values = np.ascontiguousarray(spline_arr[:, 0], dtype=c_double)
    y_values = np.ascontiguousarray(spline_arr[:, 1], dtype=c_double)

    c_success = c_int(-1)
    c_job_flag = c_int(1)  # spline mode
    c_num_data = c_int(x_values.shape[0])
    c_label = encode_string(spline_label)
    c_dummy = c_double(0.0)
    
    dll.modifyDataObject(
        c_label, byref(c_job_flag), byref(c_dummy), byref(c_num_data),
        as_ptr(x_values, c_double), as_ptr(y_values, c_double), byref(c_success)
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
        c_name_buf = create_string_buffer(CHAR_FIELD_LENGTH)
        int_info = np.zeros(1, dtype=c_int)
        double_info = np.zeros(1, dtype=c_double)

        dll.getMeasureInformation(
            byref(c_index), byref(c_job_flag),
            as_ptr(int_info, c_int), as_ptr(double_info, c_double), c_name_buf
        )
        measure_names.append(decode_string(c_name_buf.value))
    
    return measure_names


def get_measure_derivative(measure_label: str, wrt: str = "q") -> np.ndarray:
    """Get the derivative of a measure w.r.t. the generalized coordinates or velocities.

    The system must already be at the desired state via update_system() or
    update_system_at_time_index().

    Args:
        measure_label: Name of the measure
        wrt: "q" for dS/dq (generalized coordinates) or "qd" for dS/dqd
            (generalized velocities)

    Returns:
        Numpy array of shape (1, numGeneralizedCoordinates), ordered like the
        generalized coordinates (body by body: translation, rotation, flexible dofs)

    Raises:
        ValueError: If wrt is neither "q" nor "qd"
        ParameterError: If the measure is not found or the system is not updated
    """
    if wrt == "q":
        func_name = "getMeasureDerivative"
    elif wrt == "qd":
        func_name = "getMeasureDerivativeQd"
    else:
        raise ValueError(f"wrt must be 'q' or 'qd', got {wrt!r}")

    dll = get_dll()
    func = getattr(dll, func_name)

    c_success = c_int(-1)
    c_label = encode_string(measure_label)

    model_info = get_model_info()
    measure_der = np.zeros((1, model_info["numGeneralizedCoordinates"]), dtype=c_double)

    func(c_label, as_ptr(measure_der, c_double), byref(c_success))

    check_success(c_success.value, f"Get measure derivative d{measure_label}/d{wrt}", exception_class=ParameterError)

    return measure_der
