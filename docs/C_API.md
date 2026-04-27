# FreeDyn C API

This document defines the canonical location and usage rules for the FreeDyn C API.

## Canonical Header

Use the API declarations from:

- `include/freedyn/freedyn_c_api.h`

This header should be treated as the single source of truth for all bindings
(Python, MATLAB, Scilab, C/C++).

## Calling Convention and ABI

- Platform: Windows x64
- Declaration macro: `FDCIDLLMode` (`extern "C" void __declspec(... ) __stdcall`)

The API currently returns values through output parameters and success flags.

## Data and Indexing Conventions

- Prefix `i*` parameters are inputs (read-only)
- Prefix `o*` parameters are outputs (caller-owned memory)
- Dense matrix payloads are column-major in linear arrays
- Public interface indices are one-based
- Query functions are read-only and do not update model state

## Typical Lifecycle

1. `createFreeDynModel(...)`
2. `setModelAsActive(...)`
3. `getModelDofInfo(...)` and allocate arrays
4. `updateSystem(time, Q, Qd, Qdd, L, ...)`
5. Optional: `updateJacobian(...)`
6. Call query functions (`getForceVector`, `getConstraintVector`, matrix/result functions)

## Error Handling Contract

Prefer this pattern for new functions:

- `oSuccess == 1` means success
- `oSuccess == 0` means failure
- optional `oErrorMessage` buffer for diagnostics

For existing functions, preserve current behavior and document exceptions per symbol.

## Binder Guidance

For Python ctypes bindings:

1. Centralize function signatures in one module and apply `argtypes` once during initialization.
2. Keep API-name aliases (`old_name -> new_name`) in one table.
3. Perform startup symbol checks and fail fast with explicit missing-symbol messages.
4. Keep runtime operations free of signature mutation.

## Recommended Refactor in the Solver Repository

1. Split the header into stable sections:
   - model lifecycle
   - simulation control
   - state/result access
   - analysis and matrix/vector extraction
   - parameter/spline/measure access
2. Introduce explicit API version functions:
   - `getFreeDynApiVersion(int* oMajor, int* oMinor, int* oPatch)`
   - `getFreeDynApiCapabilities(char oJson[], int* oSuccess)` (optional)
3. Add one symbol naming policy and keep deprecated aliases for at least one major release.
4. Generate export lists from the header (or vice versa) to avoid drift.
5. Add an ABI smoke test executable that:
   - loads the DLL
   - resolves all required symbols
   - calls one minimal happy-path method chain

## Compatibility Policy

When renaming or changing signatures:

- keep old exports as wrappers where feasible
- annotate deprecations in the header comments
- remove deprecated exports only in a planned breaking release

## Recent Breaking Changes (2026)

- Legacy aliases removed (`setModelAsActiv`, `getStatesViaTimeIndexOfSolverResult*`, ...)
- `getModelInfos` removed; use `getModelDofInfo`
- Force/constraint/measure-derivative/result-write APIs are query-only and rely on state cached by `updateSystem`

## Packaging

Ensure release archives include `include/freedyn/freedyn_c_api.h`.
