% =========================================================================
% freedyn_api.m — FreeDyn API for MATLAB
% =========================================================================
%
% Author:  Stefan Oberpeilsteiner
% Date:    2020-04-01 (original), 2026-04 (refactored)
% License: LGPL-3.0
%
% Provides MATLAB bindings to the FreeDyn MBS solver via its C-interface
% DLL (freedyn.dll or freedyn_mt.dll).
%
% Usage:
%   addpath('bindings/matlab');
%   fh = freedyn_api(fullfile(pwd, 'bin', 'x64_MT'));
%
%   [id, err] = fh.createModel('model.fds', 'SCREEN');
%   fh.setModelAsActive(id);
%   fh.solveEoM();
%   fh.deleteModel(id);
%
% The function returns a struct of function handles for all API calls.
%
% =========================================================================

function api = freedyn_api(fdBinDirectory)
% FREEDYN_API  Initialize FreeDyn and return a struct of API function handles.
%
%   api = freedyn_api(fdBinDirectory)
%
%   fdBinDirectory  Path to the bin directory containing freedyn.dll (or
%                   freedyn_mt.dll) and FreeDynCallables.h.
%
%   Returns a struct with fields corresponding to each API function.

    addpath(fdBinDirectory);

    if ~libisloaded('FDCI_Dll')
        dllName = 'freedyn.dll';
        if ~exist(fullfile(fdBinDirectory, dllName), 'file')
            dllName = 'freedyn_mt.dll';
        end
        if ~exist(fullfile(fdBinDirectory, dllName), 'file')
            error('freedyn_api:dllNotFound', ...
                  'Neither freedyn.dll nor freedyn_mt.dll found in %s', ...
                  fdBinDirectory);
        end
        loadlibrary(fullfile(fdBinDirectory, dllName), ...
                     fullfile(fdBinDirectory, 'FreeDynCallables.h'), ...
                     'alias', 'FDCI_Dll');
    end

    % Return a named struct instead of positional outputs
    api.createModel                    = @fdApi_createModel;
    api.deleteModel                    = @fdApi_deleteModel;
    api.setModelAsActive               = @fdApi_setModelAsActive;
    api.getModelInfos                  = @fdApi_getModelInfos;
    api.generateStateVectors           = @fdApi_generateStateVectors;
    api.computeInitialConditions       = @fdApi_computeInitialConditions;
    api.modifyParameter                = @fdApi_modifyParameter;
    api.updateSystem                   = @fdApi_updateSystem;
    api.solveEoM                       = @fdApi_solveEoM;
    api.getNumTimeSteps                = @fdApi_getNumTimeSteps;
    api.getStatesAtTimeIndex           = @fdApi_getStatesAtTimeIndex;
    api.solveTimeInterval              = @fdApi_solveTimeInterval;
    api.getCurrentMeasureValue         = @fdApi_getCurrentMeasureValue;
    api.getMeasureNames                = @fdApi_getMeasureNames;
    api.generateMeasureVector          = @fdApi_generateMeasureVector;
    api.getMeasuresAtTimeIndex         = @fdApi_getMeasuresAtTimeIndex;
    api.getPhysicalDofRelatedVector    = @fdApi_getPhysicalDofRelatedVector;
    api.getLagrangeMultiplierRelatedVector = @fdApi_getLagrangeMultiplierRelatedVector;
    api.createModelRelatedMatrix       = @fdApi_createModelRelatedMatrix;
    api.getModelRelatedMatrix          = @fdApi_getModelRelatedMatrix;
    api.getDimOfModelRelatedMatrix     = @fdApi_getDimOfModelRelatedMatrix;
    api.getMeasureDerivative           = @fdApi_getMeasureDerivative;
end

% =========================================================================
%  Model management
% =========================================================================

function [modelIndex, errorString] = fdApi_createModel(path2Model, statusOutputFlag)
% Create a FreeDyn model from an .fds file.
%
%   path2Model        Path to the .fds model file.
%   statusOutputFlag  'NO', 'FILE', 'SCREEN', or 'SCREENANDFILE'.
%   modelIndex        Integer handle for the created model.
%   errorString       Error message (empty on success).

    pPath = libpointer('cstring', path2Model);
    pFlag = libpointer('cstring', statusOutputFlag);
    [~, ~, modelIndex, errorString] = calllib('FDCI_Dll', ...
        'createFreeDynModel', pPath, pFlag, -1, blanks(512));
end

function fdApi_deleteModel(modelIndex)
% Delete a previously created model.
    calllib('FDCI_Dll', 'deleteFreeDynModel', modelIndex, 0);
end

function fdApi_setModelAsActive(modelIndex)
% Set a model as the active model.
    calllib('FDCI_Dll', 'setModelAsActiv', modelIndex, 0);
end

% =========================================================================
%  Model information
% =========================================================================

function modelInfos = fdApi_getModelInfos()
% Query structural information about the active model.
%
%   Returns a struct with fields: numAllDofs, numPhyDofs, numIntDof,
%   numExtDof, numBodies, numExtConstr, numForces, numMeasures.

    [modelInfos.numAllDofs, ...
     modelInfos.numPhyDofs, ...
     modelInfos.numIntDof,  ...
     modelInfos.numExtDof,  ...
     modelInfos.numBodies,  ...
     modelInfos.numExtConstr, ...
     modelInfos.numForces,  ...
     modelInfos.numMeasures] = calllib('FDCI_Dll', 'getModelInfos', ...
                                        0, 0, 0, 0, 0, 0, 0, 0);
end

% =========================================================================
%  State vectors
% =========================================================================

function [pQ, pQd, pQdd, pL] = fdApi_generateStateVectors()
% Allocate state vectors matching the active model dimensions.
%
%   pQ    libpointer – generalised coordinates     (numPhyDofs x 1)
%   pQd   libpointer – generalised velocities      (numPhyDofs x 1)
%   pQdd  libpointer – generalised accelerations   (numPhyDofs x 1)
%   pL    libpointer – Lagrange multipliers         (numIntDof+numExtDof x 1)

    info = fdApi_getModelInfos();
    tmp  = zeros(info.numPhyDofs, 1);
    pQ   = libpointer('doublePtr', tmp);
    pQd  = libpointer('doublePtr', tmp);
    pQdd = libpointer('doublePtr', tmp);
    pL   = libpointer('doublePtr', zeros(info.numIntDof + info.numExtDof, 1));
end

function isSuc = fdApi_computeInitialConditions()
% Compute consistent initial conditions.
    isSuc = calllib('FDCI_Dll', 'computeInitialConditions', 0);
end

function isSuc = fdApi_updateSystem(t, pQ, pQd, pQdd, pLag)
% Update the system state.
    [~, ~, ~, ~, ~, isSuc] = calllib('FDCI_Dll', 'updateSystem', ...
                                      t, pQ, pQd, pQdd, pLag, 0);
end

% =========================================================================
%  Simulation
% =========================================================================

function isSuc = fdApi_solveEoM()
% Solve the full equations of motion (time period as defined in .fds).
    isSuc = calllib('FDCI_Dll', 'solveEoM', 0);
end

function isSuc = fdApi_solveTimeInterval(t1)
% Solve up to time t1 (incremental).
    [~, isSuc] = calllib('FDCI_Dll', 'solveTimeInterval', t1, 0);
end

function numTimeSteps = fdApi_getNumTimeSteps()
% Get total number of solution time steps.
    numTimeSteps = calllib('FDCI_Dll', 'getNumberOfSolutionTimeSteps', 0);
end

function time = fdApi_getStatesAtTimeIndex(timeIndex, pQ)
% Retrieve states at a given time index from the solver result.
%
%   timeIndex  0-based time step index.
%   pQ         libpointer to coordinate vector (updated in-place).
%   time       Time value at the given index.

    [~, time] = calllib('FDCI_Dll', ...
        'getStatesViaTimeIndexOfSolverResult', timeIndex, 0, pQ);
end

% =========================================================================
%  Parameters
% =========================================================================

function isSuc = fdApi_modifyParameter(parameterLabel, parameterValue)
% Modify a scalar parameter in the active model.
    pLabel = libpointer('cstring', parameterLabel);
    [~, ~, ~, ~, ~, ~, isSuc] = calllib('FDCI_Dll', 'modifyDataObject', ...
        pLabel, 2, parameterValue, 0, 0, 0, 0);
end

% =========================================================================
%  Measures
% =========================================================================

function meaVal = fdApi_getCurrentMeasureValue(measureLabel)
% Get the current value of a named measure.
    pLabel = libpointer('cstring', measureLabel);
    [~, meaVal] = calllib('FDCI_Dll', ...
        'getMeasureValueWithMeasureName', pLabel, 0, 0);
end

function meaNames = fdApi_getMeasureNames()
% Get the names of all measures in the active model.
    info = fdApi_getModelInfos();
    meaNames = cell(1, info.numMeasures);
    for i = 1:info.numMeasures
        [~, ~, ~, ~, meaNames{i}] = calllib('FDCI_Dll', ...
            'getMeasureInformation', i-1, 1, 0, 0, blanks(512));
    end
end

function pMeaVals = fdApi_generateMeasureVector()
% Allocate a measure value vector matching the active model.
    info = fdApi_getModelInfos();
    pMeaVals = libpointer('doublePtr', zeros(info.numMeasures, 1));
end

function time = fdApi_getMeasuresAtTimeIndex(timeIndex, pMeaVals)
% Retrieve all measure values at a given time index.
    [~, time] = calllib('FDCI_Dll', ...
        'getMeasuresViaTimeIndexOfSolverResult', timeIndex, 0, pMeaVals);
end

function fdApi_getMeasureDerivative(measureLabel, time, pQ, pQd, pQdd, pLag, pMeasureDer)
% Get measure derivative w.r.t. generalised coordinates.
%
%   Requires fdApi_updateSystem() to be called first.
%   pMeasureDer  libpointer receiving the derivative values.

    pLabel = libpointer('cstring', measureLabel);
    calllib('FDCI_Dll', 'getMeasureDerivative', ...
            pLabel, time, pQ, pQd, pQdd, pLag, pMeasureDer);
end

% =========================================================================
%  Advanced analysis – vectors
% =========================================================================

function fdApi_getPhysicalDofRelatedVector(vectorId, time, pQ, pQd, pQdd, pLag, pVec)
% Compute a physical-DOF-related vector (based on current state).
%
%   Requires fdApi_updateSystem() to be called first.
%
%   vectorId  Identifier:
%     1001  ACCINERTIAFORCE   M(Q)*Qdd
%     1002  CONSTRFORCE       Cq'*Lambda
%     1003  VELINERTIAFORCE   Qvv
%     1004  SUMOFEXTFORCES    Sum of external forces
%     1005  ELASTICFORCES     Elastic forces (flexible bodies)
%     1006  DAMPINGFORCES     Damping forces (flexible bodies)
%     1007  SUMOFALLFORCES    f = QExt + Qvv - Cq'L - Qelas - Qdamp

    calllib('FDCI_Dll', 'getPhysicalDofRelatedVector', ...
            vectorId, time, pQ, pQd, pQdd, pLag, pVec);
end

function fdApi_getLagrangeMultiplierRelatedVector(vectorId, time, pQ, pQd, pQdd, pLag, pVec)
% Compute a constraint-related vector (based on current state).
%
%   Requires fdApi_updateSystem() to be called first.
%
%   vectorId  Identifier:
%     1011  CONSTRERROR     C(q) – constraint residual
%     1012  DCONSTRDT       dC/dt
%     1013  DCQDTMULTQD     d(Cq)/dt * qd
%     1014  D2CONSTRDT2     d²C/dt²

    calllib('FDCI_Dll', 'getLagrangeMultiplierRelatedVector', ...
            vectorId, time, pQ, pQd, pQdd, pLag, pVec);
end

% =========================================================================
%  Advanced analysis – matrices (sparse)
% =========================================================================

function modelMatrixIndex = fdApi_createModelRelatedMatrix( ...
        nRows, nCols, nMatrices, pMatrixIds, pRowPos, pColPos, pScaling)
% Create a model-related matrix definition.
%
%   pMatrixIds  List of matrix identifiers:
%     101  MASSMAT       M(q)
%     102  DMQDDDQ       d(M*qdd)/dq
%     103  DQVVDQ        d(Qvv)/dq
%     104  DQVVDQD       d(Qvv)/dqd
%     105  DCQTLIDQ      d(Cq'*l)/dq (inner)
%     106  DSTIFFDQ      K
%     107  DDAMPDQD      D
%     108  DQEXTDQ       d(QExt)/dq
%     109  DQEXTDQD      d(QExt)/dqd
%     110  DCQTLEDQ      d(Cq'*l)/dq (external)
%     201  CQT           Cq'
%     301  CQ            Cq
%
%   pRowPos, pColPos   Block position of each matrix in the assembled matrix.
%   pScaling           Scaling factor for each sub-matrix.

    [~, ~, ~, ~, ~, ~, ~, modelMatrixIndex] = calllib('FDCI_Dll', ...
        'createModelRelatedMatrix', ...
        nRows, nCols, nMatrices, pMatrixIds, pRowPos, pColPos, pScaling, 0);
end

function [rowDim, colDim, numNonZeros] = fdApi_getDimOfModelRelatedMatrix(modelMatrixIndex)
% Get dimensions of a model-related matrix.
    [~, rowDim, colDim, numNonZeros] = calllib('FDCI_Dll', ...
        'getDimOfModelRelatedMatrix', modelMatrixIndex, 0, 0, 0);
end

function fdApi_getModelRelatedMatrix( ...
        modelMatrixIndex, rowDim, colDim, numNonZeros, nMat, pScaling, ...
        pRowInd, pColInd, pValues)
% Retrieve a model-related matrix in sparse coordinate format.
%
%   pRowInd, pColInd, pValues  libpointers receiving the sparse data.

    calllib('FDCI_Dll', 'getModelRelatedMatrix', ...
            modelMatrixIndex, rowDim, colDim, numNonZeros, nMat, pScaling, ...
            pRowInd, pColInd, pValues);
end
