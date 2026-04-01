/*
* sfuntmpl_basic.c: Basic 'C' template for a level 2 S-function.
*
* Copyright 1990-2013 The MathWorks, Inc.
*/


/*
* You must specify the S_FUNCTION_NAME as the name of your S-function
* (i.e. replace sfuntmpl_basic with the name of your S-function).
*/

#define S_FUNCTION_NAME  sfun_
#define S_FUNCTION_LEVEL 2

#include <windows.h>

/*
* Need to include simstruc.h for the definition of the SimStruct and
* its associated macro definitions.
*/
#include "simstruc.h"

// --- Declarations
typedef void (__stdcall *createFreeDynModel_type)(char[],char[],int*,char[]);
typedef void (__stdcall *deleteFreeDynModel_type)(int*,int*);
typedef void (__stdcall *setModelAsActiv_type)(int*,int*);
typedef void (__stdcall *getModelInfos_type)(int*,int*,int*,int*,int*,int*,int*,int*);
typedef void (__stdcall *computeInitialConditions_type)(int*);
typedef void (__stdcall *modifyDataObject_type)(char[],int*,double*,int*,double[],double[],int*);
typedef void (__stdcall *solveTimeInterval_type)(double*,int*);
typedef void (__stdcall *updateSystem_type)(double*,double[],double[],double[],double[],int*);
typedef void (__stdcall *getMeasureValueWithMeasureName_type)(char[],double*,int*);

struct modelInfo
{
    int NumAllDofs;
    int NumPhysicalDof;
    int NumConstraintDof;
};

HINSTANCE dllHandle = NULL;

createFreeDynModel_type createFreeDynModel_ptr = NULL; 
deleteFreeDynModel_type deleteFreeDynModel_ptr = NULL; 
setModelAsActiv_type setModelAsActiv_ptr = NULL;
getModelInfos_type getModelInfos_ptr = NULL;
computeInitialConditions_type computeInitialConditions_ptr = NULL;
modifyDataObject_type modifyDataObject_ptr = NULL; 
solveTimeInterval_type solveTimeInterval_ptr = NULL;
updateSystem_type updateSystem_ptr = NULL;
getMeasureValueWithMeasureName_type getMeasureValueWithMeasureName_ptr = NULL;

char* iPath2FdsFile;
char iStatusOutputFlag[] = "FILE";
int oModelIndex;
char oErrorMessage[512];    
int oScilabOutputDmy;
    
int oNumAllDofs;
int oNumPhysicalDof;
int oNumInternalConstraintDof;
int oNumExternalConstraintDof;
int oNumBodies;
int oNumExtConstraints;
int oNumForces;
int oNumMeasures;

struct modelInfo modelInfoModel;

double iTime;
double* ioQ;
double* ioQd;
double* ioQdd;
double* ioL;
int oSimulationFlag;

char* iPath2NewSplineData[] = {};
int iJobFlag = 2;
double idAmp[sizeof(iPath2NewSplineData)];
int dummyInt;
double dummyDouble[1];

double iT0;
double iT1;

char* iMeasureName[] = {};
double oMeasureValue[sizeof(iMeasureName)];

/* Error handling
* --------------
*
* You should use the following technique to report errors encountered within
* an S-function:
*
*       ssSetErrorStatus(S,"Error encountered due to ...");
*       return;
*
* Note that the 2nd argument to ssSetErrorStatus must be persistent memory.
* It cannot be a local variable. For example the following will cause
* unpredictable errors:
*
*      mdlOutputs()
*      {
*         char msg[256];         {ILLEGAL: to fix use "static char msg[256];"}
*         sprintf(msg,"Error due to %s", string);
*         ssSetErrorStatus(S,msg);
*         return;
*      }
*
*/

/*====================*
* S-function methods *
*====================*/

/* Function: mdlInitializeSizes ===============================================
* Abstract:
*    The sizes information is used by Simulink to determine the S-function
*    block's characteristics (number of inputs, outputs, states, etc.).
*/
static void mdlInitializeSizes(SimStruct *S)
{
    //const char_T * block_path = ssGetPath( S );
    //ssPrintf( "mdlInitializeSizes: %s.\n", block_path );

    ssSetNumSFcnParams(S, 2);  /* Number of expected parameters */
    if (ssGetNumSFcnParams(S) != ssGetSFcnParamsCount(S)) 
    {
        /* Return if number of expected != number of actual parameters */
        return;
    }

    ssSetNumContStates(S, 0);
    ssSetNumDiscStates(S, 0);

    ssSetNumSampleTimes(S, 1);
    ssSetNumRWork(S, 0);
    ssSetNumIWork(S, 0);
    ssSetNumPWork(S, 0);
    ssSetNumModes(S, 0);
    ssSetNumNonsampledZCs(S, 0);

    /* Specify the sim state compliance to be same as a built-in block */
    ssSetSimStateCompliance(S, USE_DEFAULT_SIM_STATE);

    //     ssSetOptions(S, 0);
    ssSetOptions(S,
    SS_OPTION_USE_TLC_WITH_ACCELERATOR |
    SS_OPTION_CAN_BE_CALLED_CONDITIONALLY |
    SS_OPTION_EXCEPTION_FREE_CODE |
    SS_OPTION_WORKS_WITH_CODE_REUSE |
    SS_OPTION_SFUNCTION_INLINED_FOR_RTW |
    SS_OPTION_DISALLOW_CONSTANT_SAMPLE_TIME);
}

/* Function: mdlInitializeSampleTimes =========================================
* Abstract:
*    This function is used to specify the sample time(s) for your
*    S-function. You must register the same number of sample times as
*    specified in ssSetNumSampleTimes.
*/
static void mdlInitializeSampleTimes(SimStruct *S)
{
    ssSetSampleTime(S, 0, INHERITED_SAMPLE_TIME);
    ssSetOffsetTime(S, 0, 0.0);
}

#define MDL_INITIALIZE_CONDITIONS   /* Change to #undef to remove function */
#if defined(MDL_INITIALIZE_CONDITIONS)
/* Function: mdlInitializeConditions ========================================
* Abstract:
*    In this function, you should initialize the continuous and discrete
*    states for your S-function block.  The initial states are placed
*    in the state vector, ssGetContStates(S) or ssGetRealDiscStates(S).
*    You can also perform any other initialization activities that your
*    S-function may require. Note, this routine will be called at the
*    start of simulation and if it is present in an enabled subsystem
*    configured to reset states, it will be call when the enabled subsystem
*    restarts execution to reset the states.
*/
static void mdlInitializeConditions(SimStruct *S)
{
}
#endif /* MDL_INITIALIZE_CONDITIONS */

#define MDL_START  /* Change to #undef to remove function */
#if defined(MDL_START) 
/* Function: mdlStart =======================================================
* Abstract:
*    This function is called once at start of model execution. If you
*    have states that should be initialized once, this is the place
*    to do it.
*/
static void mdlStart(SimStruct *S)
{    
    int i = 0;
    
    // --- Get file path
    const int_T flen = (int_T)mxGetN((ssGetSFcnParam(S, 1)))*sizeof(char)+1;
    iPath2FdsFile = mxMalloc(flen);
    mxGetString((ssGetSFcnParam(S,1)),iPath2FdsFile,flen); 

//     ssPrintf("Path: %s\n", iPath2FdsFile);
    
    // --- Load Library
    dllHandle = LoadLibrary(TEXT("freedyn.dll"));
    if (dllHandle == NULL)
        dllHandle = LoadLibrary(TEXT("freedyn_mt.dll"));
    
//     ssPrintf("dllHandle: %p\n", dllHandle);
    
    if (dllHandle == NULL)
    {
        ssSetErrorStatus(S, "Entered library path not valid.");
    }
    else
    {  
        // --- Pointer to Library Functions
        createFreeDynModel_ptr = (createFreeDynModel_type) GetProcAddress(dllHandle,"createFreeDynModel");
        deleteFreeDynModel_ptr = (deleteFreeDynModel_type) GetProcAddress(dllHandle,"deleteFreeDynModel");
        setModelAsActiv_ptr = (setModelAsActiv_type) GetProcAddress(dllHandle,"setModelAsActiv");
        getModelInfos_ptr = (getModelInfos_type) GetProcAddress(dllHandle,"getModelInfos");
        computeInitialConditions_ptr = (computeInitialConditions_type) GetProcAddress(dllHandle,"computeInitialConditions");
        modifyDataObject_ptr = (modifyDataObject_type) GetProcAddress(dllHandle,"modifyDataObject");
        solveTimeInterval_ptr = (solveTimeInterval_type) GetProcAddress(dllHandle,"solveTimeInterval");
        updateSystem_ptr = (updateSystem_type) GetProcAddress(dllHandle,"updateSystem");
        getMeasureValueWithMeasureName_ptr = (getMeasureValueWithMeasureName_type) GetProcAddress(dllHandle,"getMeasureValueWithMeasureName");
        
//         ssPrintf( "dll handle address: %p\n", dllHandle );
//         ssPrintf( "createFreeDynModel_ptr address: %p\n", createFreeDynModel_ptr );
//         ssPrintf( "getModelInfos_ptr: %p\n", getModelInfos_ptr );
//         ssPrintf( "computeInitialConditions_ptr address: %p\n", computeInitialConditions_ptr );
        
        // --- Create Model
        createFreeDynModel_ptr(iPath2FdsFile,iStatusOutputFlag,&oModelIndex,oErrorMessage);
        
        // --- Set Model Active
        setModelAsActiv_ptr(&oModelIndex,&oScilabOutputDmy);
        
        // --- Get Model Infos
        getModelInfos_ptr(&oNumAllDofs,&oNumPhysicalDof,&oNumInternalConstraintDof,&oNumExternalConstraintDof,&oNumBodies,&oNumExtConstraints,&oNumForces,&oNumMeasures);
       
        modelInfoModel.NumAllDofs = oNumAllDofs;
        modelInfoModel.NumPhysicalDof = oNumPhysicalDof;
        modelInfoModel.NumConstraintDof = oNumInternalConstraintDof + oNumExternalConstraintDof;
    
//         ssPrintf( "modelInfoMotorcycle.NumPhysicalDof: %d\n", modelInfoMotorcycle.NumPhysicalDof);
//         ssPrintf( "modelInfoMotorcycle.NumConstraintDof: %d\n", modelInfoMotorcycle.NumConstraintDof);
        
        // --- Adapt size of arrays
        ioQ = (double*) malloc(modelInfoModel.NumPhysicalDof * sizeof(double));
        ioQd = (double*) malloc(modelInfoModel.NumPhysicalDof * sizeof(double));
        ioQdd = (double*) malloc(modelInfoModel.NumPhysicalDof * sizeof(double));
        ioL = (double*) malloc(modelInfoModel.NumConstraintDof * sizeof(double));
            
        // --- Compute Initial Conditions 
        computeInitialConditions_ptr(&oSimulationFlag);
        
    }
}
#endif /*  MDL_START */

/* Function: mdlOutputs =======================================================
* Abstract:
*    In this function, you compute the outputs of your S-function
*    block.
*/
static void mdlOutputs(SimStruct *S, int_T tid)
{      
    // --- Define Inputs
    
    // --- Define Outputs
    
    // --- Write Outputs
    
    // --- Read Inputs
}

#define MDL_UPDATE  /* Change to #undef to remove function */
#if defined(MDL_UPDATE)
/* Function: mdlUpdate ======================================================
* Abstract:
*    This function is called once for every major integration time step.
*    Discrete states are typically updated here, but this function is useful
*    for performing any tasks that should only take place once per
*    integration step.
*/
static void mdlUpdate(SimStruct *S, int_T tid)
{
    double deltaT = (double)mxGetScalar(ssGetSFcnParam(S,0));
    
    iT0 = 0.0 + ssGetT(S);
    iT1 = iT0 + deltaT;
    
//     ssPrintf("idAmp: %f %f\n",iT0,iT1);
    
    // --- Modify Data Object
    
    // --- Solve Time Interval
    solveTimeInterval_ptr(&iT1,&oSimulationFlag);
    
    // --- Update System
    if(oSimulationFlag == 1 )
	{
		//updateSystem_ptr(&iT1,ioQ,ioQd,ioQdd,ioL,&oSimulationFlag);
	}
	else
    	ssSetErrorStatus(S, "ERROR in iteration.");
}
#endif /* MDL_UPDATE */

#undef MDL_DERIVATIVES  /* Change to #undef to remove function */
#if defined(MDL_DERIVATIVES)
/* Function: mdlDerivatives =================================================
* Abstract:
*    In this function, you compute the S-function block's derivatives.
*    The derivatives are placed in the derivative vector, ssGetdX(S).
*/
static void mdlDerivatives(SimStruct *S)
{
}
#endif /* MDL_DERIVATIVES */

/* Function: mdlTerminate =====================================================
* Abstract:
*    In this function, you should perform any actions that are necessary
*    at the termination of a simulation.  For example, if memory was
*    allocated in mdlStart, this is the place to free it.
*/
static void mdlTerminate(SimStruct *S)
{
    deleteFreeDynModel_ptr(&oModelIndex,&oScilabOutputDmy);
    FreeLibrary(dllHandle);
}

/*=============================*
* Required S-function trailer *
*=============================*/

#ifdef  MATLAB_MEX_FILE    /* Is this file being compiled as a MEX-file? */
#include "simulink.c"      /* MEX-file interface mechanism */
#else
#include "cg_sfun.h"       /* Code generation registration function */
#endif
