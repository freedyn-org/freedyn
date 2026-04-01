% #######################################################################
% FreeDyn 2 Simulink
% #######################################################################
%
% Author: Manuel Dück
% Date: 09.03.2020
%
% This file contains all necessary functions to generate a S-Function 
% of your FreeDyn model for Simulink
%
% IMPORTANT:
% 1.) copy the following files in your project directory:
%       - initFreeDyn2Simulink.m 
%
% 2.) enter at section "USER INPUT":
%       - name of the .fds file
%       - desired inputs and outputs
%       - path of the FreeDynAPI "..\FreeDynAPI"
%
% 3.) Run this script (Press F5)
%
% 4.) Work with your FreeDyn model in Simulink
%
% #######################################################################
%%
clear;clc; 
%%
% #######################################################################
% ########################## USER INPUT #################################
% #######################################################################

% Model name of your .fds file (without file extension)
model.name = 'V8ControlledRunUp';

% Enter desired inputs/outputs
model.inputs = ["amp_controller"]; % string array of inputs
model.outputs = ["phi","omega"]; % string array of outputs

% Enter the full path of the "..\FreeDynAPI" folder
freeDynApiPath = '...\FreeDynAPI';

% #######################################################################
% #######################################################################
% #######################################################################

%%
disp('### FreeDyn 2 Simulink ###'); disp('Processing...');
cd(strrep(mfilename('fullpath'),'\initFreeDyn2Simulink',''));

% add paths
libraryPath = [freeDynApiPath, '\bin'];
addpath(genpath(freeDynApiPath));
addpath(genpath(cd(strrep(mfilename('fullpath'),'\initFreeDyn2Simulink',''))));

% call main function => get function handles
[checkUserInputsOK,...
 getStepTime,...
 genSFun,...
 genSFunBlock] = fcnsFreeDyn2Simulink();

% Checks on user inputs
if ~checkUserInputsOK(model.name,model.inputs,model.outputs,libraryPath)
    return
end
    
% Model path
model.path = strcat(insertAfter(pwd,'\','\'),'\\',model.name,'.fds');

% Add path of the FreeDyn libraries
if ~contains(getenv('PATH'),libraryPath)
    setenv('PATH', [getenv('PATH'), libraryPath, ';'])
end

% Read step time out of .fds file
Ts = getStepTime(model.path);

% Generate C code for S-Function
genSFun(model.name,model.inputs,model.outputs);
mex(['sfun_',model.name,'.c']); 
delete(['sfun_',model.name,'.c']);
pause(0.1)
clc; disp('### FreeDyn 2 Simulink ###'); disp('Processing...');

% Generate S-Function block
genSFunBlock(model.name,model.inputs,model.outputs);

clc; disp('### FreeDyn 2 Simulink ###'); disp('Completed successfully.');