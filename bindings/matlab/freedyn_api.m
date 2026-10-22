% =========================================================================
% freedyn_api.m — FreeDyn API for MATLAB
% =========================================================================
%
% Author:  Stefan Oberpeilsteiner
% Date:    2020-04-01 (original), 2026-04 (refactored), 2026-10 (C-API v1 port)
% License: LGPL-3.0
%
% Provides MATLAB bindings to the FreeDyn MBS solver via its C-interface
% DLL (freedyn.dll or freedyn_mt.dll), see include/freedyn/freedyn_c_api.h.
%
% Usage:
%   addpath('bindings/matlab');
%   fh = freedyn_api(fullfile(pwd, 'bin', 'x64_MT'));
%
%   [id, err] = fh.createModel('model.fds', 'SCREEN');
%   fh.setModelAsActive(id);
%   fh.solveEoM();
%   fh.updateSystemAtTimeIndex(fh.getNumTimeSteps() - 1);
%   dSdq = fh.getMeasureDerivative('myMeasure');
%   fh.deleteModel(id);
%
% The function returns a struct of function handles for all API calls.
% Time step indices are zero-based (as in the Python bindings), vectors are
% returned as MATLAB arrays. Failing calls raise an error.
%
% =========================================================================

function api = freedyn_api(fdBinDirectory, fdHeaderFile)
% FREEDYN_API  Initialize FreeDyn and return a struct of API function handles.
%
%   api = freedyn_api(fdBinDirectory)
%   api = freedyn_api(fdBinDirectory, fdHeaderFile)
%
%   fdBinDirectory  Path to the bin directory containing freedyn.dll (or
%                   freedyn_mt.dll) and its dependent DLLs.
%   fdHeaderFile    Optional path to freedyn_c_api.h. Default: searched in
%                   fdBinDirectory and in include/freedyn of the repository.
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
        if nargin < 2 || isempty(fdHeaderFile)
            fdHeaderFile = findHeader(fdBinDirectory);
        end
        loadlibrary(fullfile(fdBinDirectory, dllName), ...
                    createCHeader(fdHeaderFile), ...
                    'alias', 'FDCI_Dll');
    end

    % Return a named struct instead of positional outputs
    api.createModel                    = @fdApi_createModel;
    api.deleteModel                    = @fdApi_deleteModel;
    api.setModelAsActive               = @fdApi_setModelAsActive;
    api.resetActiveModelForRerun       = @fdApi_resetActiveModelForRerun;
    api.getModelInfos                  = @fdApi_getModelInfos;
    api.generateStateVectors           = @fdApi_generateStateVectors;
    api.computeInitialConditions       = @fdApi_computeInitialConditions;
    api.modifyParameter                = @fdApi_modifyParameter;
    api.updateSystem                   = @fdApi_updateSystem;
    api.updateSystemAtTimeIndex        = @fdApi_updateSystemAtTimeIndex;
    api.solveEoM                       = @fdApi_solveEoM;
    api.getNumTimeSteps                = @fdApi_getNumTimeSteps;
    api.getStatesAtTimeIndex           = @fdApi_getStatesAtTimeIndex;
    api.solveTimeInterval              = @fdApi_solveTimeInterval;
    api.getCurrentMeasureValue         = @fdApi_getCurrentMeasureValue;
    api.getMeasureNames                = @fdApi_getMeasureNames;
    api.getMeasuresAtTimeIndex         = @fdApi_getMeasuresAtTimeIndex;
    api.getMeasureDerivative           = @fdApi_getMeasureDerivative;
    api.getForceVector                 = @fdApi_getForceVector;
    api.getConstraintVector            = @fdApi_getConstraintVector;
    api.createModelRelatedMatrix       = @fdApi_createModelRelatedMatrix;
    api.getModelRelatedMatrix          = @fdApi_getModelRelatedMatrix;
    api.getDimOfModelRelatedMatrix     = @fdApi_getDimOfModelRelatedMatrix;
end

% =========================================================================
%  Library loading helpers
% =========================================================================

function headerFile = findHeader(fdBinDirectory)
% Locate freedyn_c_api.h next to the DLL or in the repository include dir.
    thisDir = fileparts(mfilename('fullpath'));
    candidates = { ...
        fullfile(fdBinDirectory, 'freedyn_c_api.h'), ...
        fullfile(fdBinDirectory, '..', '..', 'include', 'freedyn', 'freedyn_c_api.h'), ...
        fullfile(thisDir, '..', '..', 'include', 'freedyn', 'freedyn_c_api.h')};
    for i = 1:numel(candidates)
        if exist(candidates{i}, 'file')
            headerFile = candidates{i};
            return;
        end
    end
    error('freedyn_api:headerNotFound', ...
          'freedyn_c_api.h not found. Pass its path as second argument.');
end

function cHeaderFile = createCHeader(headerFile)
% loadlibrary parses the header as C, but FDCIDLLMode expands to
% 'extern "C" ...'. Write a copy with a C-compatible macro to tempdir.
    txt = fileread(headerFile);
    txt = regexprep(txt, '#ifdef FDCIDLLBUILD.*?#endif', ...
                    '#define FDCIDLLMode void __stdcall', 'once');
    cHeaderFile = fullfile(tempdir, 'freedyn_c_api_matlab.h');
    fid = fopen(cHeaderFile, 'w');
    fwrite(fid, txt);
    fclose(fid);
end

function checkSuccess(isSuc, what)
% Raise an error if a C-API call reported failure.
    if isSuc ~= 1
        error('freedyn_api:callFailed', '%s failed.', what);
    end
end

% =========================================================================
%  Model management
% =========================================================================

function [modelIndex, errorString] = fdApi_createModel(path2Model, statusOutputFlag)
% Create a FreeDyn model from an .fds file.
%
%   path2Model        Path to the .fds model file.
%   statusOutputFlag  'No', 'File', 'Screen', or 'ScreenAndFile'.
%   modelIndex        Integer handle for the created model (-1 on failure).
%   errorString       Error message (empty on success).

    [~, ~, modelIndex, errorString] = calllib('FDCI_Dll', ...
        'createFreeDynModel', path2Model, statusOutputFlag, -1, blanks(512));
    errorString = strtrim(errorString);
end

function fdApi_deleteModel(modelIndex)
% Delete a previously created model.
    [~, isSuc] = calllib('FDCI_Dll', 'deleteFreeDynModel', modelIndex, 0);
    checkSuccess(isSuc, 'deleteFreeDynModel');
end

function fdApi_setModelAsActive(modelIndex)
% Set a model as the active model.
    [~, isSuc] = calllib('FDCI_Dll', 'setModelAsActive', modelIndex, 0);
    checkSuccess(isSuc, 'setModelAsActive');
end

function fdApi_resetActiveModelForRerun()
% Reset the active model for a clean rerun (e.g. after parameter changes).
    isSuc = calllib('FDCI_Dll', 'resetActiveModelForRerun', 0);
    checkSuccess(isSuc, 'resetActiveModelForRerun');
end

% =========================================================================
%  Model information
% =========================================================================

function modelInfos = fdApi_getModelInfos()
% Query the dimensions of the active model.
%
%   Returns a struct with fields: numGeneralizedCoordinates,
%   numLagrangeMultipliers, numBodyStates, numBodies, numExtConstr,
%   numForces, numMeasures.

    [modelInfos.numGeneralizedCoordinates, ...
     modelInfos.numLagrangeMultipliers, ...
     modelInfos.numBodyStates, ...
     modelInfos.numBodies, ...
     modelInfos.numExtConstr, ...
     modelInfos.numForces, ...
     modelInfos.numMeasures, ...
     isSuc] = calllib('FDCI_Dll', 'getModelDofInfo', 0, 0, 0, 0, 0, 0, 0, 0);
    checkSuccess(isSuc, 'getModelDofInfo');
end

% =========================================================================
%  State vectors
% =========================================================================

function [Q, Qd, Qdd, L] = fdApi_generateStateVectors()
% Allocate state vectors matching the active model dimensions.
%
%   Q, Qd, Qdd  generalized coordinates/velocities/accelerations (numGeneralizedCoordinates x 1)
%   L           Lagrange multipliers (numLagrangeMultipliers x 1)

    info = fdApi_getModelInfos();
    Q   = zeros(info.numGeneralizedCoordinates, 1);
    Qd  = Q;
    Qdd = Q;
    L   = zeros(info.numLagrangeMultipliers, 1);
end

function fdApi_computeInitialConditions()
% Compute consistent initial conditions.
    isSuc = calllib('FDCI_Dll', 'computeInitialConditions', 0);
    checkSuccess(isSuc, 'computeInitialConditions');
end

function fdApi_updateSystem(t, Q, Qd, Qdd, L)
% Update the system to time t and the given states. Required before
% querying measure derivatives, force/constraint vectors or matrices.
    [~, ~, ~, ~, ~, isSuc] = calllib('FDCI_Dll', 'updateSystem', ...
                                      t, Q, Qd, Qdd, L, 0);
    checkSuccess(isSuc, 'updateSystem');
end

function fdApi_updateSystemAtTimeIndex(timeIndex)
% Update the system to the solver result at a stored time step (zero-based).
    [~, isSuc] = calllib('FDCI_Dll', 'updateSystemAtTimeIndex', timeIndex + 1, 0);
    checkSuccess(isSuc, 'updateSystemAtTimeIndex');
end

% =========================================================================
%  Simulation
% =========================================================================

function fdApi_solveEoM()
% Solve the full equations of motion (time period as defined in .fds).
    isSuc = calllib('FDCI_Dll', 'solveEoM', 0);
    checkSuccess(isSuc, 'solveEoM');
end

function fdApi_solveTimeInterval(t1)
% Solve up to time t1 (incremental).
    [~, isSuc] = calllib('FDCI_Dll', 'solveTimeInterval', t1, 0);
    checkSuccess(isSuc, 'solveTimeInterval');
end

function numTimeSteps = fdApi_getNumTimeSteps()
% Get total number of stored solution time steps.
    [numTimeSteps, isSuc] = calllib('FDCI_Dll', 'getNumberOfSolutionTimeSteps', 0, 0);
    checkSuccess(isSuc, 'getNumberOfSolutionTimeSteps');
end

function [time, Q, Qd, Qdd, L] = fdApi_getStatesAtTimeIndex(timeIndex)
% Retrieve the solver states at a stored time step.
%
%   timeIndex  Zero-based time step index.
%   time       Time value at the given index.

    [Q, Qd, Qdd, L] = fdApi_generateStateVectors();
    [~, time, Q, Qd, Qdd, L, isSuc] = calllib('FDCI_Dll', ...
        'getGeneralizedStatesAtTimeIndex', timeIndex + 1, 0, Q, Qd, Qdd, L, 0);
    checkSuccess(isSuc, 'getGeneralizedStatesAtTimeIndex');
end

% =========================================================================
%  Parameters
% =========================================================================

function fdApi_modifyParameter(parameterLabel, parameterValue)
% Modify a scalar parameter in the active model.
    [~, ~, ~, ~, ~, ~, isSuc] = calllib('FDCI_Dll', 'modifyDataObject', ...
        parameterLabel, 2, parameterValue, 0, 0, 0, 0);
    checkSuccess(isSuc, ['modifyDataObject(' parameterLabel ')']);
end

% =========================================================================
%  Measures
% =========================================================================

function meaVal = fdApi_getCurrentMeasureValue(measureLabel)
% Get the current value of a named measure (after updateSystem).
    [~, meaVal, isSuc] = calllib('FDCI_Dll', ...
        'getMeasureValueWithMeasureName', measureLabel, 0, 0);
    checkSuccess(isSuc, ['getMeasureValueWithMeasureName(' measureLabel ')']);
end

function meaNames = fdApi_getMeasureNames()
% Get the names of all measures in the active model.
    info = fdApi_getModelInfos();
    meaNames = cell(1, info.numMeasures);
    for i = 1:info.numMeasures
        [~, ~, ~, ~, name] = calllib('FDCI_Dll', ...
            'getMeasureInformation', i-1, 1, 0, 0, blanks(512));
        meaNames{i} = strtrim(name);
    end
end

function [time, meaVals] = fdApi_getMeasuresAtTimeIndex(timeIndex)
% Retrieve all measure values at a stored time step (zero-based).
    info = fdApi_getModelInfos();
    [~, time, meaVals, isSuc] = calllib('FDCI_Dll', ...
        'getMeasuresAtTimeIndex', timeIndex + 1, 0, zeros(info.numMeasures, 1), 0);
    checkSuccess(isSuc, 'getMeasuresAtTimeIndex');
end

function measureDer = fdApi_getMeasureDerivative(measureLabel, wrt)
% Get the derivative of a measure (after updateSystem / updateSystemAtTimeIndex).
%
%   wrt         'q' (default) for dS/dq or 'qd' for dS/dqd.
%   measureDer  Row vector (1 x numGeneralizedCoordinates), ordered like the
%               generalized coordinates (body by body: translation, rotation,
%               flexible dofs).

    if nargin < 2
        wrt = 'q';
    end
    switch wrt
        case 'q'
            funcName = 'getMeasureDerivative';
        case 'qd'
            funcName = 'getMeasureDerivativeQd';
        otherwise
            error('freedyn_api:invalidArgument', 'wrt must be ''q'' or ''qd''.');
    end
    info = fdApi_getModelInfos();
    [~, measureDer, isSuc] = calllib('FDCI_Dll', funcName, measureLabel, ...
        zeros(1, info.numGeneralizedCoordinates), 0);
    checkSuccess(isSuc, [funcName '(' measureLabel ')']);
end

% =========================================================================
%  Advanced analysis – vectors (after updateSystem)
% =========================================================================

function vec = fdApi_getForceVector(forceType)
% Compute a force vector in generalized coordinate space.
%
%   forceType:
%     'ACCINERTIAFORCE'   M(Q)*Qdd
%     'CONSTRFORCE'       Cq'*Lambda
%     'VELINERTIAFORCE'   Qvv
%     'SUMOFEXTFORCES'    Sum of external forces
%     'ELASTICFORCES'     Elastic forces (flexible bodies)
%     'DAMPINGFORCES'     Damping forces (flexible bodies)
%     'SUMOFALLFORCES'    QExt + Qvv - Cq'L - Qelas - Qdamp
%     '<paramName>'       dQext/d(param)
%   The prefix 'MBS_' of the C-API names is optional.

    known = {'ACCINERTIAFORCE', 'CONSTRFORCE', 'VELINERTIAFORCE', ...
             'SUMOFEXTFORCES', 'ELASTICFORCES', 'DAMPINGFORCES', 'SUMOFALLFORCES'};
    if any(strcmp(forceType, known))
        forceType = ['MBS_' forceType];
    end
    info = fdApi_getModelInfos();
    [~, vec, isSuc] = calllib('FDCI_Dll', 'getForceVector', forceType, ...
        zeros(info.numGeneralizedCoordinates, 1), 0);
    checkSuccess(isSuc, ['getForceVector(' forceType ')']);
end

function vec = fdApi_getConstraintVector(constraintQuantity)
% Compute a constraint-related vector.
%
%   constraintQuantity:
%     'CONSTRERROR'    C(q) – constraint residual
%     'DCONSTRDT'      dC/dt
%     'DCQDTMULTQD'    d(Cq)/dt * qd
%     'D2CONSTRDT2'    d²C/dt²
%   The prefix 'MBS_' of the C-API names is optional.

    if ~startsWith(constraintQuantity, 'MBS_')
        constraintQuantity = ['MBS_' constraintQuantity];
    end
    info = fdApi_getModelInfos();
    [~, vec, isSuc] = calllib('FDCI_Dll', 'getConstraintVector', constraintQuantity, ...
        zeros(info.numLagrangeMultipliers, 1), 0);
    checkSuccess(isSuc, ['getConstraintVector(' constraintQuantity ')']);
end

% =========================================================================
%  Advanced analysis – matrices (sparse)
% =========================================================================

function modelMatrixIndex = fdApi_createModelRelatedMatrix( ...
        nRows, nCols, matrixIds, rowPos, colPos, scaling)
% Create a model-related matrix definition.
%
%   nRows, nCols  Number of block rows/columns of the assembled matrix.
%   matrixIds     List of matrix identifiers:
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
%   rowPos, colPos  Block position of each matrix in the assembled matrix.
%   scaling         Scaling factor for each sub-matrix.

    [~, ~, ~, ~, ~, ~, ~, modelMatrixIndex] = calllib('FDCI_Dll', ...
        'createModelRelatedMatrix', nRows, nCols, numel(matrixIds), ...
        int32(matrixIds), int32(rowPos), int32(colPos), double(scaling), 0);
end

function [rowDim, colDim, numNonZeros] = fdApi_getDimOfModelRelatedMatrix(modelMatrixIndex)
% Get dimensions of a model-related matrix (after updateSystem).
    [~, rowDim, colDim, numNonZeros] = calllib('FDCI_Dll', ...
        'getDimOfModelRelatedMatrix', modelMatrixIndex, 0, 0, 0);
end

function M = fdApi_getModelRelatedMatrix(modelMatrixIndex)
% Retrieve a model-related matrix (after updateSystem) as MATLAB sparse matrix.
    [rowDim, colDim, numNonZeros] = fdApi_getDimOfModelRelatedMatrix(modelMatrixIndex);
    [~, rowPtr, colInd, values] = calllib('FDCI_Dll', 'getModelRelatedMatrix', ...
        modelMatrixIndex, zeros(rowDim + 1, 1, 'int32'), ...
        zeros(numNonZeros, 1, 'int32'), zeros(numNonZeros, 1));
    % CSR3 with one-based indices -> row index of every non-zero
    rowInd = repelem((1:rowDim)', diff(double(rowPtr)));
    M = sparse(rowInd, double(colInd), values, rowDim, colDim);
end
