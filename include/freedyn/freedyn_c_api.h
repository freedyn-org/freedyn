// FreeDyn C-Interface (FDCI) DLL
// Functionality for interfacing with FreeDyn
// Compatible with the current release of FreeDyn
// Maintained by Stefan Oberpeilsteiner
// Developed by Wolfgang Witteveen & Thomas Lauss
//
// Conventions:
// 1) Input parameters: prefix i (read only during the entire function call)
// 2) Output parameters: prefix o (caller must provide fields of correct length)
// 3) Dense matrices are stored column-major in flat arrays
// 4) All indices are ONE-BASED in this interface (Scilab, Matlab convention)
// 5) oSuccess: 1 = success, 0 = failure (present in every function that can fail)
// 6) All pointer arguments must be valid (non-null) unless explicitly documented otherwise
// 7) Query functions are read-only and never set model states
//
// Vector dimensions (query via getModelDofInfo):
//   Q, Qd, Qdd  : length = oNumGeneralizedCoordinates
//   L            : length = oNumLagrangeMultipliers  (= inner + external constraint DOF)
//   BodyStates   : length = oNumBodyStates           (= sum of 12+nFlex per body, for visualization)
//
// Typical call lifecycle:
//   1) createFreeDynModel(...)
//   2) setModelAsActive(...)
//   3) getModelDofInfo(...) and allocate caller-side arrays
//   4) updateSystem(time, Q, Qd, Qdd, L, ...)
//   5) Optional: updateJacobian(...) for Jacobian-only refresh at cached state
//   6) Call read-only query functions (forces, constraints, measures, matrices, result IO)
//
// Breaking API changes (2026):
//   - Legacy aliases removed (setModelAsActiv, getStatesViaTimeIndexOfSolverResult*, ...)
//   - getModelInfos removed; use getModelDofInfo
//   - Force/constraint/measure-derivative/result-write APIs are query-only now:
//       state/time are provided via updateSystem, not passed repeatedly to query calls

#ifdef FDCIDLLBUILD
	#define FDCIDLLMode extern "C" void __declspec(dllexport) __stdcall
#else
	#define FDCIDLLMode extern "C" void __declspec(dllimport) __stdcall
#endif

//=========================================================================
//=========================================================================
// MODEL MANAGEMENT - X2FreeDyn_ModelManagement.cpp
//=========================================================================
//=========================================================================

/// Create a FreeDyn model from an FDS file
/**
* @param[in]    iPath2FdsFile       char*   Full path to the .fds solver file
* @param[in]    iStatusOutputFlag   char*   "No" | "ScreenAndFile" | "Screen" | "File"
* @param[out]   oModelIndex         int*    Index of the created model (one-based), -1 on failure
* @param[out]   oErrorMessage       char*   Error description on failure. Minimum field length: 512
*/
FDCIDLLMode createFreeDynModel(char iPath2FdsFile[],
                               char iStatusOutputFlag[],
                               int* oModelIndex,
                               char oErrorMessage[]);

/// Set model as active. All subsequent calls operate on this model.
/**
* @param[in]  iModelIndex  int*  Index of model to activate (one-based)
* @param[out] oSuccess     int*  1 if successful, 0 if index out of range
*/
FDCIDLLMode setModelAsActive(int* iModelIndex, int* oSuccess);

/// Delete a FreeDyn model and free all associated resources
/**
* @param[in]  iModelIndex  int*  Index of model to delete (one-based)
* @param[out] oSuccess     int*  1 if successful, 0 if index out of range
*/
FDCIDLLMode deleteFreeDynModel(int* iModelIndex, int* oSuccess);

/// Recreate active model internals for a clean rerun after data changes
/**
* Performs a clean rerun reset on the currently active model without calling
* create(), and without deleting/recreating the model handle.
* Intended for changed parameters/splines/inputs with unchanged topology.
*
* Note: with unchanged topology, model-related matrix mappings remain valid.
*
* @param[out] oSuccess  int*  1 if successful, 0 on error
*/
FDCIDLLMode resetActiveModelForRerun(int* oSuccess);

//=========================================================================
//=========================================================================
// MODEL INFORMATION - X2FreeDyn_Model.cpp
//=========================================================================
//=========================================================================

/// Get model DOF information (dimensions for all state vectors)
/**
* This is the primary function for determining array sizes for all other FDCI calls.
*
* @param[out] oNumGeneralizedCoordinates  int*  Length of Q, Qd, Qdd vectors (7 per rigid body: 3 pos + 4 Euler params)
* @param[out] oNumLagrangeMultipliers     int*  Length of L vector (inner + external constraint DOF)
* @param[out] oNumBodyStates              int*  Length of BodyStates vector (12 per rigid body: 3 pos + 9 rot matrix entries)
* @param[out] oNumBodies                  int*  Number of bodies
* @param[out] oNumExtConstraints          int*  Number of external constraints
* @param[out] oNumForces                  int*  Number of external forces
* @param[out] oNumMeasures                int*  Number of measures
* @param[out] oSuccess                    int*  1 if successful, 0 on error
*/
FDCIDLLMode getModelDofInfo(int* oNumGeneralizedCoordinates,
                            int* oNumLagrangeMultipliers,
                            int* oNumBodyStates,
                            int* oNumBodies,
                            int* oNumExtConstraints,
                            int* oNumForces,
                            int* oNumMeasures,
                            int* oSuccess);

/// Update the multibody system state and recompute all internal quantities
/**
* Sets the current state of the system to the provided vectors and updates
* equation-of-motion related quantities (mass/forces/constraints/sensors).
* Jacobian matrices are updated separately via updateJacobian().
* This is one entry point that updates the cached state/time used by
* read-only query functions.
*
* @param[in]  iTime     double*  Current simulation time
* @param[in]  iQ        double*  Generalized coordinates      (length: oNumGeneralizedCoordinates)
* @param[in]  iQd       double*  Generalized velocities       (length: oNumGeneralizedCoordinates)
* @param[in]  iQdd      double*  Generalized accelerations    (length: oNumGeneralizedCoordinates)
* @param[in]  iL        double*  Lagrange multipliers         (length: oNumLagrangeMultipliers)
* @param[out] oSuccess  int*     1 if successful, 0 on error
*/
FDCIDLLMode updateSystem(double* iTime, double iQ[], double iQd[], double iQdd[], double iL[], int* oSuccess);

/// Restore solver state at a stored time step and update all internal quantities
/**
* Reads state vectors from the solver result container at iTimeStepIndex,
* writes them into cached vectors, and executes the same internal system update
* as updateSystem().
*
* @param[in]  iTimeStepIndex  int*  Time step index (one-based, range: 1..oNumOfTimeSteps)
* @param[out] oSuccess        int*  1 if successful, 0 on error
*/
FDCIDLLMode updateSystemAtTimeIndex(int* iTimeStepIndex, int* oSuccess);

/// Update Jacobian matrices at the current cached state
/**
* Recomputes Jacobian-related quantities using the current state/time cached
* by the most recent successful call to updateSystem().
* Does not change cached state/time.
*
* @param[out] oSuccess  int*  1 if successful, 0 on error
*/
FDCIDLLMode updateJacobian(int* oSuccess);

/// Get error string of active model
/**
* @param[out] oErrorString  char*  Error message. Minimum field length: 512.
* @param[out] oSuccess      int*   1 if successful, 0 on error
*/
FDCIDLLMode getModelErrorString(char oErrorString[], int* oSuccess);

/// Get warning string of active model
/**
* @param[out] oWarningString  char*  Warning message. Minimum field length: 512.
* @param[out] oSuccess        int*   1 if successful, 0 on error
*/
FDCIDLLMode getModelWarningString(char oWarningString[], int* oSuccess);

//=========================================================================
//=========================================================================
// DATA OBJECTS - X2FreeDyn_DataObject.cpp
//=========================================================================
//=========================================================================

/// Modify a data object (parameter value or spline data)
/**
* @param[in]  iDataObjectLabel   char*    Label of the data object
* @param[in]  iJobFlag           int*     1 = modify spline, 2 = modify parameter
* @param[in]  iNewParValue       double*  New parameter value (only for iJobFlag=2)
* @param[in]  iNumOfDataPoints   int*     Number of spline data points (only for iJobFlag=1)
* @param[in]  iDataX             double*  X-data of spline (only for iJobFlag=1)
* @param[in]  iDataY             double*  Y-data of spline (only for iJobFlag=1)
* @param[out] oSuccess           int*     1 if successful, 0 on error
*/
FDCIDLLMode modifyDataObject(char iDataObjectLabel[],
                             int* iJobFlag,
                             double* iNewParValue,
                             int* iNumOfDataPoints,
                             double iDataX[],
                             double iDataY[],
                             int* oSuccess);

/// Get parameter information
/**
* @param[in]  iParameterIndex  int*    Index of the parameter (one-based)
* @param[in]  iJobFlag         int*    1 = get parameter label (oCharInfos, min 256), 2 = get count (oIntInfos)
* @param[out] oIntInfos        int*    Integer information
* @param[out] oDoubleInfos     double* Double information (reserved)
* @param[out] oCharInfos       char*   Char information
*/
FDCIDLLMode getParameterInformation(int* iParameterIndex,
                                    int* iJobFlag,
                                    int oIntInfos[],
                                    double oDoubleInfos[],
                                    char oCharInfos[]);

//=========================================================================
//=========================================================================
// MEASURES - X2FreeDyn_Measures.cpp
//=========================================================================
//=========================================================================

/// Get measure information
/**
* @param[in]  iMeasureIndex  int*    Index of the measure (zero-based)
* @param[in]  iJobFlag       int*    1 = get measure name (oCharInfos, min 256), 2 = get count (oIntInfos)
* @param[out] oIntInfos      int*    Integer information
* @param[out] oDoubleInfos   double* Double information (reserved)
* @param[out] oCharInfos     char*   Char information
*/
FDCIDLLMode getMeasureInformation(int* iMeasureIndex,
                                  int* iJobFlag,
                                  int oIntInfos[],
                                  double oDoubleInfos[],
                                  char oCharInfos[]);

/// Get current measure value by name. Requires prior call to updateSystem.
/**
* @param[in]  iMeasureName    char*    Name/Label of the measure
* @param[out] oMeasureValue   double*  Current measure value
* @param[out] oSuccess        int*     1 if successful, 0 on error
*/
FDCIDLLMode getMeasureValueWithMeasureName(char iMeasureName[], double* oMeasureValue, int* oSuccess);

/// Compute measure derivative w.r.t. generalized coordinates. Requires prior call to updateSystem.
/**
* Uses cached state/time from the latest successful updateSystem() call.
*
* @param[in]  iMeasureLabel  char*    Label of the measure
* @param[out] oMeasureDer    double*  Derivative w.r.t. all gen. coords (length: oNumGeneralizedCoordinates)
* @param[out] oSuccess       int*     1 if successful, 0 on error
*/
FDCIDLLMode getMeasureDerivative(char iMeasureLabel[],
                                 double oMeasureDer[], int* oSuccess);

//=========================================================================
//=========================================================================
// SOLVER - X2FreeDyn_Solver.cpp
//=========================================================================
//=========================================================================

/// Solve equations of motion (full time range defined in .fds)
/**
* @param[out] oSuccess  int*  1 if successful, 0 on error
*/
FDCIDLLMode solveEoM(int* oSuccess);

/// Compute initial conditions
/**
* @param[out] oSuccess  int*  1 if successful, 0 on error
*/
FDCIDLLMode computeInitialConditions(int* oSuccess);

/// Solve for a time interval [current_time, iT1]
/**
* @param[in]  iT1       double*  End time of interval
* @param[out] oSuccess  int*     1 if successful, 0 on error
*/
FDCIDLLMode solveTimeInterval(double* iT1, int* oSuccess);

/// Get number of stored solution time steps
/**
* @param[out] oNumOfTimeSteps  int*  Number of stored time steps (0 if no simulation)
* @param[out] oSuccess         int*  1 if successful, 0 on error
*/
FDCIDLLMode getNumberOfSolutionTimeSteps(int* oNumOfTimeSteps, int* oSuccess);

/// Get simulation time value at a stored time step
/**
* @param[in]  iTimeStepIndex  int*     Time step index (one-based, range: 1..oNumOfTimeSteps)
* @param[out] oTime           double*  Simulation time at this step
* @param[out] oSuccess        int*     1 if successful, 0 on error
*/
FDCIDLLMode getTime(int* iTimeStepIndex, double* oTime, int* oSuccess);

/// Get body states (position + rotation matrix) at a stored time step
/**
* Returns body states in visualization format: [3 pos + 9 rot matrix + nFlex per body]
* Array length: oNumBodyStates (from getModelDofInfo)
*
* @param[in]  iTimeStepIndex  int*     Time step index (one-based, range: 1..oNumOfTimeSteps)
* @param[out] oTime           double*  Simulation time at this step
* @param[out] oBodyStates     double*  Body states array
* @param[out] oSuccess        int*     1 if successful, 0 on error
*/
FDCIDLLMode getBodyStatesAtTimeIndex(int* iTimeStepIndex,
                                     double* oTime,
                                     double oBodyStates[],
                                     int* oSuccess);

/// Get generalized state vectors (Q, Qd, Qdd, L) at a stored time step
/**
* Array lengths: Q/Qd/Qdd = oNumGeneralizedCoordinates, L = oNumLagrangeMultipliers (from getModelDofInfo)
*
* @param[in]  iTimeStepIndex  int*     Time step index (one-based, range: 1..oNumOfTimeSteps)
* @param[out] oTime           double*  Simulation time at this step
* @param[out] oQ              double*  Generalized coordinates
* @param[out] oQd             double*  Generalized velocities
* @param[out] oQdd            double*  Generalized accelerations
* @param[out] oL              double*  Lagrange multipliers
* @param[out] oSuccess        int*     1 if successful, 0 on error
*/
FDCIDLLMode getGeneralizedStatesAtTimeIndex(int* iTimeStepIndex,
                                            double* oTime,
                                            double oQ[],
                                            double oQd[],
                                            double oQdd[],
                                            double oL[],
                                            int* oSuccess);

/// Get measure values at a stored time step
/**
* Array length: oNumMeasures (from getModelDofInfo)
*
* @param[in]  iTimeStepIndex  int*     Time step index (one-based, range: 1..oNumOfTimeSteps)
* @param[out] oTime           double*  Simulation time at this step
* @param[out] oMeasures       double*  Measure values
* @param[out] oSuccess        int*     1 if successful, 0 on error
*/
FDCIDLLMode getMeasuresAtTimeIndex(int* iTimeStepIndex, double* oTime, double oMeasures[], int* oSuccess);

//=========================================================================
//=========================================================================
// FORCE & CONSTRAINT VECTORS - X2FreeDyn_Model.cpp
// Require prior call to updateSystem.
//=========================================================================
//=========================================================================

/// Get a force vector in generalized coordinate space
/**
* Requires prior call to updateSystem.
* Uses cached state/time from the latest successful updateSystem() call.
*
* @param[in]  iForceType       char*    Which force vector to compute:
*                                        "MBS_ACCINERTIAFORCE"  - M(Q)*Qdd
*                                        "MBS_CONSTRFORCE"      - CqT*Lambda
*                                        "MBS_VELINERTIAFORCE"  - Qvv
*                                        "MBS_SUMOFEXTFORCES"   - Sum of external forces
*                                        "MBS_ELASTICFORCES"    - Elastic forces (flex bodies)
*                                        "MBS_DAMPINGFORCES"    - Damping forces (flex bodies)
*                                        "MBS_SUMOFALLFORCES"   - QExt + Qvv - CqTL - Qelas - Qdamp
*                                        "<paramName>"          - dQext/d(param)
* @param[out] oForceVector     double*  Result force vector          (length: oNumGeneralizedCoordinates)
* @param[out] oSuccess         int*     1 if successful, 0 on error
*/
FDCIDLLMode getForceVector(char iForceType[],
                               double oForceVector[], int* oSuccess);

/// Get a constraint-related vector
/**
* Requires prior call to updateSystem.
* Uses cached state/time from the latest successful updateSystem() call.
*
* @param[in]  iConstraintQuantity  char*    Which quantity to compute:
*                                            "MBS_CONSTRERROR"   - C(q) constraint residuum
*                                            "MBS_DCONSTRDT"     - dC/dt
*                                            "MBS_DCQDTMULTQD"   - d(Cq)/dt * Qd
*                                            "MBS_D2CONSTRDT2"   - d^2C/dt^2
* @param[out] oConstraintVector    double*  Result vector                (length: oNumLagrangeMultipliers)
* @param[out] oSuccess             int*     1 if successful, 0 on error
*/
FDCIDLLMode getConstraintVector(char iConstraintQuantity[],
                                    double oConstraintVector[], int* oSuccess);

//=========================================================================
//=========================================================================
// JACOBIAN MATRICES - X2FreeDyn_Model.cpp
//=========================================================================
//=========================================================================

/// Create a composed model matrix (sparse Jacobian) for repeated evaluation
/**
* @param[in]  iRow                      int*     Number of block rows
* @param[in]  iCol                      int*     Number of block columns
* @param[in]  iNumOfMatricesToBeMapped  int*     Number of sub-matrices to compose
* @param[in]  iMatrixIdentifier         int[]    Matrix type IDs (101=M, 102=dMqdd/dq, ..., 301=Cq)
* @param[in]  iRowPosition              int[]    Block row position per sub-matrix
* @param[in]  iColPosition              int[]    Block column position per sub-matrix
* @param[in]  iScalingValue             double[] Scaling factor per sub-matrix
* @param[out] oModelMatrixIndex         int*     Index of created matrix (for later retrieval)
*/
FDCIDLLMode createModelRelatedMatrix(int* iRow, int* iCol, int* iNumOfMatricesToBeMapped,
                                     int iMatrixIdentifier[], int iRowPosition[], int iColPosition[],
                                     double iScalingValue[], int* oModelMatrixIndex);

/// Get dimensions of a model-related matrix
/**
* @param[in]  iModelMatrixIndex  int*  Index returned by createModelRelatedMatrix
* @param[out] oRowDim            int*  Number of rows
* @param[out] oColDim            int*  Number of columns
* @param[out] oNumNonZeros       int*  Number of non-zero entries
*/
FDCIDLLMode getDimOfModelRelatedMatrix(int* iModelMatrixIndex, int* oRowDim, int* oColDim, int* oNumNonZeros);

/// Get model-related matrix data in sparse CSR3 format (one-based indices)
/**
* @param[in]  iModelMatrixIndex  int*      Index returned by createModelRelatedMatrix
* @param[out] oRowInd            int[]     Row pointer array (length: oRowDim + 1)
* @param[out] oColInd            int[]     Column indices (length: oNumNonZeros)
* @param[out] oValues            double[]  Non-zero values (length: oNumNonZeros)
*/
FDCIDLLMode getModelRelatedMatrix(int* iModelMatrixIndex, int oRowInd[], int oColInd[], double oValues[]);

//=========================================================================
//=========================================================================
// RESULT FILE OUTPUT - X2FreeDyn_Misc.cpp
//=========================================================================
//=========================================================================

/// Write states to FreeDyn GUI result file format
/**
* @param[in]  iIOJobFlag              int*     1 = open file, 2 = write current state, 3 = close file
* @param[in]  iFileTemplate           char*    Base filename template (min length: 1024). Used with iIOJobFlag=1.
* @param[in]  iRequestedFilePattern   int[]    Length 7: [vel, acc, force, constrForce, lagrange, measures, states]
*                                           Used with iIOJobFlag=1.
*                                           For iIOJobFlag=2, data is written from cached state/time
*                                           created by updateSystem().
* @param[out] oSuccess                int*     1 if successful, 0 on error
*/
FDCIDLLMode writeResultFile(int* iIOJobFlag, char iFileTemplate[], int iRequestedFilePattern[],
                            int* oSuccess);
