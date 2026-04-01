// =========================================================================
// freedyn_api.sce — FreeDyn API for Scilab
// =========================================================================
//
// Author:  Stefan Oberpeilsteiner
// Date:    2020-04-01 (original), 2026-04 (refactored)
// License: LGPL-3.0
//
// Provides Scilab bindings to the FreeDyn MBS solver via its C-interface
// DLL (freedyn_mt.dll, static CRT / MT variant).
//
// Usage:
//   exec("freedyn_api.sce", -1);
//   fdApi(fullfile(pwd(), "bin", "x64_MT"));
//
//   [id, err] = fdApi_createModel("model.fds", "SCREEN");
//   fdApi_setModelAsActive(id);
//   // ... work with model ...
//   fdApi_deleteModel(id);
//
// =========================================================================

// -------------------------------------------------------------------------
//  Initialisation
// -------------------------------------------------------------------------

// Initialize the FreeDyn Scilab API by loading the solver DLL.
//
// @param fdBinDirectory  Path to the bin directory that contains
//                        freedyn_mt.dll (x64_MT build) and its
//                        dependencies.
// @return bSuccessful    %t if DLL loaded successfully, %f otherwise.
//
function bSuccessful = fdApi(fdBinDirectory)
    // Return immediately if already loaded
    [bOK, ilib] = c_link("createFreeDynModel");
    if bOK then
        bSuccessful = %t;
        return;
    end

    // Temporarily add bin directory to PATH so dependencies are found
    envPathPreLink = getenv("PATH");
    setenv("PATH", fdBinDirectory + ";" + envPathPreLink);

    // Prefer freedyn_mt.dll (static CRT), fall back to freedyn.dll
    dllName = "freedyn_mt.dll";
    if ~isfile(fullfile(fdBinDirectory, dllName)) then
        dllName = "freedyn.dll";
    end

    dllPath = fullfile(fdBinDirectory, dllName);
    if ~isfile(dllPath) then
        setenv("PATH", envPathPreLink);
        error("fdApi: DLL not found: " + dllPath);
    end

    // Parse exported function names from the header file
    hdrPath = fullfile(fdBinDirectory, "FreeDynCallables.h");
    if ~isfile(hdrPath) then
        setenv("PATH", envPathPreLink);
        error("fdApi: Header not found: " + hdrPath);
    end

    ilib = link(dllPath, _fdApi_parseDllFunctions(hdrPath), "c");

    // Restore original PATH
    setenv("PATH", envPathPreLink);

    // Verify
    [bOK, ilib] = c_link("createFreeDynModel");
    bSuccessful = bOK;
endfunction

// -------------------------------------------------------------------------
//  Internal helpers
// -------------------------------------------------------------------------

// Parse DLL function names from FreeDynCallables.h.
// (internal – not meant for direct use)
//
function dllFunctions = _fdApi_parseDllFunctions(headerFile)
    fd = mopen(headerFile);
    dllFunctions = [];
    curLine = mgetl(fd, 1);
    while ~meof(fd)
        line = stripblanks(curLine);
        if line ~= "" & strstr(curLine, "FDCIDLLMode") == curLine then
            funcName = strsubst(curLine, "FDCIDLLMode ", "");
            funcName = strsubst(funcName, strstr(curLine, "("), "");
            dllFunctions($+1) = funcName;
        end
        curLine = mgetl(fd, 1);
    end
    mclose(fd);
endfunction

// -------------------------------------------------------------------------
//  Model management
// -------------------------------------------------------------------------

// Create a FreeDyn model from an .fds file.
//
// @param path2Model       Path to the .fds model file.
// @param statusOutputFlag "NO", "FILE", "SCREEN", or "SCREENANDFILE".
// @return modelIndex      Integer handle for the created model.
// @return errorString     Error message (empty on success).
//
function [modelIndex, errorString] = fdApi_createModel(path2Model, statusOutputFlag)
    [modelIndex, errorString] = call("createFreeDynModel", ...
        path2Model,       1, "c", ...
        statusOutputFlag, 2, "c", ...
        "out", [1,1], 3, "i", ...
               [512,1], 4, "c");
endfunction

// Delete a previously created model.
//
// @param modelIndex  Handle returned by fdApi_createModel.
//
function fdApi_deleteModel(modelIndex)
    call("deleteFreeDynModel", modelIndex, 1, "i", "out", [1,1], 2, "i");
endfunction

// Set a model as the active model. All subsequent API calls operate
// on the active model.
//
// @param modelIndex  Handle returned by fdApi_createModel.
//
function fdApi_setModelAsActive(modelIndex)
    call("setModelAsActiv", modelIndex, 1, "i", "out", [1,1], 2, "i");
endfunction

// -------------------------------------------------------------------------
//  Model information
// -------------------------------------------------------------------------

// Query structural information about the active model.
//
// @return modelInfos  Struct with fields: numAllDofs, numPhyDofs,
//                     numIntDof, numExtDof, numBodies, numExtConstr,
//                     numForces, numMeasures.
//
function modelInfos = fdApi_getModelInfos()
    [modelInfos.numAllDofs,  ...
     modelInfos.numPhyDofs,  ...
     modelInfos.numIntDof,   ...
     modelInfos.numExtDof,   ...
     modelInfos.numBodies,   ...
     modelInfos.numExtConstr,...
     modelInfos.numForces,   ...
     modelInfos.numMeasures] = call("getModelInfos", ...
        "out", [1,1], 1, "i", ...
               [1,1], 2, "i", ...
               [1,1], 3, "i", ...
               [1,1], 4, "i", ...
               [1,1], 5, "i", ...
               [1,1], 6, "i", ...
               [1,1], 7, "i", ...
               [1,1], 8, "i");
endfunction

// -------------------------------------------------------------------------
//  State vectors
// -------------------------------------------------------------------------

// Allocate state vectors matching the active model dimensions.
//
// @return vQ    Generalised coordinates      (numPhyDofs x 1)
// @return vQd   Generalised velocities       (numPhyDofs x 1)
// @return vQdd  Generalised accelerations    (numPhyDofs x 1)
// @return vLag  Lagrange multipliers         (numIntDof+numExtDof x 1)
//
function [vQ, vQd, vQdd, vLag] = fdApi_generateStateVecs()
    info = fdApi_getModelInfos();
    vQ   = zeros(info.numPhyDofs, 1);
    vQd  = zeros(info.numPhyDofs, 1);
    vQdd = zeros(info.numPhyDofs, 1);
    vLag = zeros(info.numIntDof + info.numExtDof, 1);
endfunction

// Compute consistent initial conditions.
//
// @return isSuc  1 if successful, 0 otherwise.
//
function isSuc = fdApi_computeInitialConditions()
    isSuc = call("computeInitialConditions", "out", [1,1], 1, "i");
endfunction

// Update the system state (positions, velocities, accelerations, multipliers).
//
// @param t     Current time.
// @param iQ    Generalised coordinates.
// @param iQd   Generalised velocities.
// @param iQdd  Generalised accelerations.
// @param iLag  Lagrange multipliers.
// @return isSuc  1 if successful.
//
function isSuc = fdApi_updateSystem(t, iQ, iQd, iQdd, iLag)
    isSuc = call("updateSystem", ...
        t,    1, "d", ...
        iQ,   2, "d", ...
        iQd,  3, "d", ...
        iQdd, 4, "d", ...
        iLag, 5, "d", ...
        "out", [1,1], 6, "i");
endfunction

// -------------------------------------------------------------------------
//  Simulation
// -------------------------------------------------------------------------

// Solve the full equations of motion (time period as defined in .fds).
//
// @return isSuc  1 if successful.
//
function isSuc = fdApi_solveEoM()
    isSuc = call("solveEoM", "out", [1,1], 1, "i");
endfunction

// Solve up to time t1 (incremental).
//
// @param t1  End time of the interval.
// @return isSuc  1 if successful.
//
function isSuc = fdApi_solveTimeInterval(t1)
    isSuc = call("solveTimeInterval", t1, 1, "d", "out", [1,1], 2, "i");
endfunction

// Get total number of solution time steps.
//
// @return numTimeSteps  Integer count.
//
function numTimeSteps = fdApi_getNumTimeSteps()
    numTimeSteps = call("getNumberOfSolutionTimeSteps", "out", [1,1], 1, "i");
endfunction

// Retrieve states at a given time index from the solver result.
//
// @param iTimeIndex  0-based time step index.
// @param iQ          Pre-allocated coordinate vector (from fdApi_generateStateVecs).
// @return time       Time value at the given index.
// @return Q          Generalised coordinates at the given index.
//
function [time, Q] = fdApi_getStatesAtTimeInd(iTimeIndex, iQ)
    [time, Q] = call("getStatesViaTimeIndexOfSolverResult", ...
        iTimeIndex, 1, "i", ...
        "out", [1,1], 2, "d", ...
               size(iQ), 3, "d");
endfunction

// -------------------------------------------------------------------------
//  Parameters and data objects
// -------------------------------------------------------------------------

// Modify a scalar parameter in the active model.
//
// @param parameterName   Label of the parameter.
// @param parameterValue  New value (double).
// @return isSuc  1 if successful.
//
function isSuc = fdApi_modifyParameter(parameterName, parameterValue)
    isSuc = call("modifyDataObject", ...
        parameterName,  1, "c", ...
        2,              2, "i", ...   // type 2 = scalar parameter
        parameterValue, 3, "d", ...
        0,              4, "i", ...
        0,              5, "d", ...
        0,              6, "d", ...
        "out", [1,1], 7, "i");
endfunction

// Modify a spline data object in the active model.
//
// @param splineLabel  Label of the spline.
// @param splineData   (N x 2) matrix – column 1: x, column 2: y.
// @return isSuc  1 if successful.
//
function isSuc = fdApi_modifySpline(splineLabel, splineData)
    nData = size(splineData, 1);
    isSuc = call("modifyDataObject", ...
        splineLabel,      1, "c", ...
        1,                2, "i", ...   // type 1 = spline
        0.,               3, "d", ...
        nData,            4, "i", ...
        splineData(:,1),  5, "d", ...
        splineData(:,2),  6, "d", ...
        "out", [1,1], 7, "i");
endfunction

// -------------------------------------------------------------------------
//  Measures
// -------------------------------------------------------------------------

// Get the current value of a named measure.
//
// @param measureName  Label of the measure.
// @return meaVal      Current measure value (double).
//
function meaVal = fdApi_getCurrentMeaVal(measureName)
    [meaVal, success] = call("getMeasureValueWithMeasureName", ...
        measureName, 1, "c", ...
        "out", [1,1], 2, "d", ...
               [1,1], 3, "i");
endfunction

// Get the names of all measures in the active model.
//
// @return measureNames  String vector of measure labels.
//
function measureNames = fdApi_getMeasureNames()
    info = fdApi_getModelInfos();
    measureNames = emptystr(info.numMeasures);
    for i = 1:info.numMeasures
        measureNames(i) = call("getMeasureInformation", ...
            i-1, 1, "i", ...
            1,   2, "i", ...
            0,   3, "i", ...
            0,   4, "i", ...
            "out", [512,1], 5, "c");
    end
endfunction

// Allocate a measure value vector matching the active model.
//
// @return vMeaVals  (numMeasures x 1) zero vector.
//
function vMeaVals = fdApi_generateMeaVec()
    info = fdApi_getModelInfos();
    vMeaVals = zeros(info.numMeasures, 1);
endfunction

// Retrieve all measure values at a given time index.
//
// @param timeIndex  0-based time step index.
// @param iMeaVals   Pre-allocated measure vector (from fdApi_generateMeaVec).
// @return time      Time value at the given index.
// @return vMeaVals  Measure values at the given index.
//
function [time, vMeaVals] = fdApi_getMeaAtTimeIndex(timeIndex, iMeaVals)
    [time, vMeaVals] = call("getMeasuresViaTimeIndexOfSolverResult", ...
        timeIndex, 1, "i", ...
        "out", [1,1], 2, "d", ...
               size(iMeaVals), 3, "d");
endfunction
