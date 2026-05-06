"""
High-level FreeDyn Model class and utilities.

This is the main user-facing API for FreeDyn simulations. Use the Model
class for most applications.
"""

from typing import Dict, List, Tuple
from pathlib import Path
import numpy as np

from . import _core
from .exceptions import ModelError, SimulationError, StateError


class ModelInfo:
    """Container for model information and metadata.
    
    Attributes:
        num_generalized_coordinates: Length of Q, Qd, Qdd
        num_lagrange_multipliers: Length of L
        num_body_states: Length of body-state vector output
        num_bodies: Number of bodies in model
        num_ext_constraints: Number of external constraints
        num_forces: Number of forces
        num_measures: Number of measures
    """

    __slots__ = [
        "num_generalized_coordinates",
        "num_lagrange_multipliers",
        "num_body_states",
        "num_bodies",
        "num_ext_constraints",
        "num_forces",
        "num_measures",
        "num_all_dofs",
        "num_phy_dofs",
        "num_int_dof",
        "num_ext_dof",
        "num_ext_constr",
    ]

    def __init__(self, info_dict: Dict[str, int]):
        """Initialize from dictionary (typically from _core.get_model_info())."""
        self.num_generalized_coordinates = info_dict["numGeneralizedCoordinates"]
        self.num_lagrange_multipliers = info_dict["numLagrangeMultipliers"]
        self.num_body_states = info_dict["numBodyStates"]
        self.num_bodies = info_dict["numBodies"]
        self.num_ext_constraints = info_dict["numExtConstraints"]
        self.num_forces = info_dict["numForces"]
        self.num_measures = info_dict["numMeasures"]

        # Backward-compatible aliases
        self.num_all_dofs = info_dict.get("numAllDofs", self.num_generalized_coordinates + self.num_lagrange_multipliers)
        self.num_phy_dofs = info_dict.get("numPhyDofs", self.num_generalized_coordinates)
        self.num_int_dof = info_dict.get("numIntDof", 0)
        self.num_ext_dof = info_dict.get("numExtDof", self.num_lagrange_multipliers)
        self.num_ext_constr = info_dict.get("numExtConstr", self.num_ext_constraints)
    
    def __repr__(self) -> str:
        return (
            f"ModelInfo(bodies={self.num_bodies}, "
            f"gen_coords={self.num_generalized_coordinates}, "
            f"constraints={self.num_ext_constraints})"
        )


class Model:
    """High-level FreeDyn simulation model.
    
    This class provides a Pythonic interface to FreeDyn simulations with
    automatic resource management.
    
    Example:
        >>> fd.initialize()
        >>> with Model('model.fds') as model:
        ...     model.solve()
        ...     model.fetch_states_at_index(0)
        ...     print(model.t, model.Q)
    """

    __slots__ = [
        "fds_file_path",
        "model_index",
        "_info",
        "_t",
        "_Q",
        "_Qd",
        "_Qdd",
        "_L",
        "_is_deleted",
    ]
    
    def __init__(self, fds_file_path: str, status_output: str = 'SCREEN'):
        """Initialize a FreeDyn model.
        
        Args:
            fds_file_path: Path to .fds model file
            status_output: Output mode ('SCREEN', 'FILE', 'NO', 'SCREENANDFILE')
            
        Raises:
            ModelError: If model creation fails
        """
        self._is_deleted = True  # set early to keep __del__ safe on failures
        self.fds_file_path = Path(fds_file_path)
        self.model_index = _core.create_model(str(self.fds_file_path), status_output)
        _core.set_model_active(self.model_index)
        self._info = ModelInfo(_core.get_model_info())
        n_q = self._info.num_generalized_coordinates
        n_l = self._info.num_lagrange_multipliers
        self._t: float = 0.0
        self._Q: np.ndarray = np.zeros((n_q, 1))
        self._Qd: np.ndarray = np.zeros((n_q, 1))
        self._Qdd: np.ndarray = np.zeros((n_q, 1))
        self._L: np.ndarray = np.zeros((n_l, 1))
        self._is_deleted = False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.delete()
        return False
    
    def __del__(self):
        """Ensure model is deleted when garbage collected."""
        if not getattr(self, "_is_deleted", True):
            self.delete()
    
    def __repr__(self) -> str:
        return f"Model({self.fds_file_path.name}, index={self.model_index})"
    
    def delete(self) -> None:
        """Delete the model and clean up C resources.
        
        Called automatically when using context manager or on garbage collection.
        Safe to call multiple times.
        """
        if not self._is_deleted and self.model_index >= 0:
            try:
                _core.delete_model(self.model_index)
                self._is_deleted = True
            except ModelError:
                pass  # Already deleted or invalid
    
    def get_info(self) -> ModelInfo:
        """Get model information.
        
        Returns:
            ModelInfo object with model statistics
        """
        return self._info
    
    # ========================================================================
    # Simulation Control
    # ========================================================================
    
    def compute_initial_conditions(self) -> None:
        """Compute initial conditions for the model.
        
        Raises:
            SimulationError: If computation fails
        """
        _core.compute_initial_conditions()
    
    def solve(self) -> None:
        """Solve equations of motion for entire time period.
        
        Raises:
            SimulationError: If solving fails
        """
        _core.solve_equations_of_motion()

    def solve_until(self, end_time: float) -> None:
        """Solve simulation until specified time.
        
        Args:
            end_time: Target time for simulation
            
        Raises:
            SimulationError: If solving fails
        """
        _core.solve_time_interval(end_time)

    def reset_for_rerun(self) -> None:
        """Reset the active model internals for a clean rerun after data changes.

        Use this after changing parameters, splines, or similar inputs when the
        model topology itself has not changed.

        Raises:
            ModelError: If the DLL does not support this operation or it fails
        """
        _core.reset_active_model_for_rerun()
    
    def get_num_time_steps(self) -> int:
        """Get number of time steps from last simulation.
        
        Returns:
            Number of time steps
        """
        return _core.get_num_time_steps()
    
    # ========================================================================
    # State Management
    # ========================================================================
    
    def fetch_states_at_index(self, time_index: int) -> None:
        """Fetch state vectors from C-API by index and store as model members.

        After calling this, access the results via the properties t, Q, Qd, Qdd, L.

        Args:
            time_index: Time step index (0-based)

        Raises:
            StateError: If retrieval fails
        """
        _states = {"Q": self._Q, "Qd": self._Qd, "Qdd": self._Qdd, "L": self._L}
        self._t = _core.get_states_at_time_index_full(time_index, _states)

    @property
    def t(self) -> float:
        """Time value of last fetch_states_at_index call."""
        return self._t

    @property
    def Q(self) -> np.ndarray:
        """Generalized coordinates of last fetch_states_at_index call."""
        return self._Q

    @property
    def Qd(self) -> np.ndarray:
        """Generalized velocities of last fetch_states_at_index call."""
        return self._Qd

    @property
    def Qdd(self) -> np.ndarray:
        """Generalized accelerations of last fetch_states_at_index call."""
        return self._Qdd

    @property
    def L(self) -> np.ndarray:
        """Lagrange multipliers of last fetch_states_at_index call."""
        return self._L



    def get_time_at_index(self, time_index: int) -> float:
        """Get only the simulation time value at a specific time index.

        Args:
            time_index: Time step index (0-based)

        Returns:
            Time value at index

        Raises:
            StateError: If retrieval fails
        """
        return _core.get_time_at_index(time_index)
    
    def update_state(self, time: float, states: Dict[str, np.ndarray]) -> None:
        """Update system to specific time with given states.
        
        Args:
            time: Time value
            states: State dictionary with Q, Qd, Qdd, L
            
        Raises:
            StateError: If update fails
        """
        _core.update_system(time, states)

    def update_state_at_index(self, time_index: int) -> None:
        """Restore cached solver state directly from a stored result index.

        Args:
            time_index: Time step index (0-based)

        Raises:
            StateError: If restoration fails
        """
        _core.update_system_at_time_index(time_index)

    def update_jacobian(self) -> None:
        """Recompute Jacobian matrices at the current cached system state.

        Call after update_state() or update_state_at_index() when Jacobian-dependent
        quantities (e.g. constraint matrices) need to be refreshed without changing
        the cached state.

        Raises:
            StateError: If the DLL does not support this operation or it fails.
        """
        _core.update_jacobian()

    def iterate_time_steps(self):
        """Generator to iterate through all time steps in results.

        Fetches each time step via :meth:`fetch_states_at_index` and yields the
        time index. Access t, Q, Qd, Qdd, L on the model directly after each step.

        Yields:
            time_index (int) for each time step
        """
        num_steps = self.get_num_time_steps()
        for i in range(num_steps):
            self.fetch_states_at_index(i)
            yield i
    
    # ========================================================================
    # Parameters and Measures
    # ========================================================================
    
    def set_parameter(self, param_name: str, value: float) -> None:
        """Set model parameter value.
        
        Args:
            param_name: Name of parameter
            value: New parameter value
            
        Raises:
            ParameterError: If parameter modification fails
        """
        _core.modify_parameter(param_name, value)

    def get_parameter_names(self) -> List[str]:
        """Get all available parameter names.

        Returns:
            List of parameter names

        Raises:
            ParameterError: If the DLL does not support parameter introspection
        """
        return _core.get_parameter_names()
    
    def set_spline(self, spline_name: str, x_values: np.ndarray, y_values: np.ndarray) -> None:
        """Set spline data.
        
        Args:
            spline_name: Name of spline
            x_values: X coordinates (1D array)
            y_values: Y coordinates (1D array)
            
        Raises:
            ParameterError: If spline modification fails
        """
        spline_data = np.column_stack([x_values, y_values])
        _core.modify_spline(spline_name, spline_data)
    
    def get_measure_value(self, measure_name: str) -> float:
        """Get value of a measure.
        
        Args:
            measure_name: Name of measure
            
        Returns:
            Measure value
            
        Raises:
            ParameterError: If measure not found
        """
        return _core.get_measure_value(measure_name)
    
    def get_measure_names(self) -> List[str]:
        """Get all available measure names.
        
        Returns:
            List of measure names
        """
        return _core.get_measure_names()
    
    def create_measure_vector(self) -> np.ndarray:
        """Create array for storing measure values.
        
        Returns:
            Numpy array of zeros with shape (num_measures, 1)
        """
        info = self.get_info()
        return np.zeros((info.num_measures, 1))
