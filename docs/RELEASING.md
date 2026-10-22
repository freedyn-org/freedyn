# Releasing FreeDyn

How the binaries get from the private `me` build tree to PyPI and the GitHub release.

## 1. Build the public configurations in `me`

Build both configurations completely (all libraries, the API DLL is built last):

```bat
cd C:\me\batchbuild
00_FreeDynInputArgumentBuild.bat Release_public
00_FreeDynInputArgumentBuild.bat Release_Static_public
```

| Folder in this repo | `me` configuration      | Contents                                                        |
|---------------------|-------------------------|-----------------------------------------------------------------|
| `bin/x64_MD`        | `Release_public`        | `FreeDyn.exe`, `Freedyn_GUI.exe`, `freedyn.dll`, kernel DLLs, Intel MKL/compiler/TBB and wxWidgets runtime |
| `bin/x64_MT`        | `Release_Static_public` | `freedyn_mt.dll`, kernel DLLs, Intel OpenMP/TBB runtime          |

## 2. Collect the binaries

```powershell
.\scripts\collect_binaries.ps1 -DryRun   # check what would be copied
.\scripts\collect_binaries.ps1
```

The script mirrors `me\batchbuild\20_PrepareFreeDynPublicRelease.bat` (and 220/221/222):

- refuses to mix builds: a kernel DLL newer than the API DLL of its configuration
  stems from a later build and may not be ABI compatible -> rebuild the configuration
- empties `bin/x64_MD` / `bin/x64_MT` before copying and writes a `BUILD_INFO.txt`
  with the `me` commit
- updates `include/freedyn/freedyn_c_api.h` from `me`; if it changed, check the
  Python, MATLAB and Scilab bindings and commit the header

`bin/` is gitignored, only the header change shows up in git.

## 3. Release

```powershell
.\scripts\release.ps1 -Version 1.2.3 -DryRun              # build the wheel only
.\scripts\release.ps1 -Version 1.2.3 -PyPIRepo testpypi   # dry run on TestPyPI
.\scripts\release.ps1 -Version 1.2.3 -PyPIRepo pypi
```

`release.ps1` tags the version, builds one `py3-none-win_amd64` wheel for all
Python 3 versions (`setup.py` copies `bin/x64_MD/*.dll`
without the GUI-only DLLs into the package), uploads it with `twine` and creates the
GitHub release with `FreeDyn-win-x64_MD.zip` and `FreeDyn-win-x64_MT.zip`.
The working tree must be clean.
