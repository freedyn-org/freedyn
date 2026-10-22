<#
.SYNOPSIS
    Collect FreeDyn binaries from the me build tree into bin/x64_MD and bin/x64_MT.

.DESCRIPTION
    Copies the public build outputs of the private "me" repository into this
    repository, so that release.ps1 can build the wheel and the GitHub release
    assets from them:

      bin/x64_MD  <- configuration Release_public        (dynamic CRT, Python + GUI)
      bin/x64_MD  <- FreeDyn.exe, Freedyn_GUI.exe, freedyn.dll, kernel DLLs,
                     Intel MKL/compiler/TBB runtime, wxWidgets runtime
      bin/x64_MT  <- configuration Release_Static_public (static CRT, standalone)
      bin/x64_MT  <- freedyn_mt.dll, kernel DLLs, Intel OpenMP/TBB runtime

    The file lists mirror me\batchbuild\20_PrepareFreeDynPublicRelease.bat and
    its helpers 220/221/222. Build both configurations in me first, e.g.
      me\batchbuild\00_FreeDynInputArgumentBuild.bat Release_public
      me\batchbuild\00_FreeDynInputArgumentBuild.bat Release_Static_public

    The target folder is emptied before copying (unless -NoClean), a
    BUILD_INFO.txt records the me commit, and include/freedyn/freedyn_c_api.h
    is updated from me (unless -SkipHeader).

.PARAMETER MeRoot
    Root of the me repository. Default: C:\me

.PARAMETER Variant
    MD, MT or Both. Default: Both

.PARAMETER DryRun
    Only list what would be copied, change nothing.

.PARAMETER NoClean
    Keep existing files in the target folders.

.PARAMETER SkipHeader
    Do not update include/freedyn/freedyn_c_api.h.

.EXAMPLE
    .\scripts\collect_binaries.ps1 -DryRun
    .\scripts\collect_binaries.ps1
    .\scripts\collect_binaries.ps1 -Variant MD -MeRoot D:\src\me
#>
param(
    [string]$MeRoot = "C:\me",
    [ValidateSet("MD", "MT", "Both")][string]$Variant = "Both",
    [switch]$DryRun,
    [switch]$NoClean,
    [switch]$SkipHeader
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Die([string]$msg)  { Write-Error $msg; exit 1 }

$IntelRoot = "C:\Program Files (x86)\Intel\oneAPI"
$MklBin    = Join-Path $IntelRoot "mkl\latest\bin"
$CmpBin    = Join-Path $IntelRoot "compiler\latest\bin"
$TbbBin    = Join-Path $IntelRoot "tbb\latest\bin"
$WxBin     = "C:\vcpkg\installed\x64-windows\bin"

# Kernel DLLs: MBS_Dll comes from the *_public configuration, the others from
# the corresponding non-public one (see 220_CopyFreeDynLibraries.bat).
# TIR_Dll is not part of public releases.
function Get-KernelDlls([string]$publicConfig, [string]$buildConfig) {
    return @(
        (Join-Path $MeRoot "mbs\simulation\SIM_Dll\bin\$buildConfig\SIM_Dll.dll"),
        (Join-Path $MeRoot "mbs\mbskernel\MBS_Dll\bin\$publicConfig\MBS_Dll.dll"),
        (Join-Path $MeRoot "mbs\solver\SOL_Dll\bin\$buildConfig\SOL_Dll.dll"),
        (Join-Path $MeRoot "mbs\data\DAT_Dll\bin\$buildConfig\DAT_Dll.dll"),
        (Join-Path $MeRoot "mbs\contact\rigidcontact\PCM_Dll\bin\$buildConfig\PCM_Dll.dll"),
        (Join-Path $MeRoot "math\exprTk\exprTk_Dll\bin\$buildConfig\exprTk_Dll.dll")
    )
}

function Get-SourceFiles([string]$variant) {
    $logo = Join-Path $MeRoot "mbs\gui_old\data\StartUpLogo.png"
    if ($variant -eq "MD") {
        $cfg = "Release_public"
        $files = @(
            (Join-Path $MeRoot "mbs\freedyn\bin\$cfg\FreeDyn.exe"),
            (Join-Path $MeRoot "mbs\gui_old\bin\$cfg\Freedyn_GUI.exe"),
            (Join-Path $MeRoot "mbs\freedyn_c_interface\freedyn_c_api\bin\$cfg\freedyn.dll"),
            $logo
        ) + (Get-KernelDlls $cfg "Release")
        $files += @("libimalloc.dll", "mkl_intel_thread.2.dll", "mkl_avx2.2.dll", "mkl_vml_avx2.2.dll",
                    "mkl_core.2.dll", "mkl_sequential.2.dll", "mkl_def.2.dll", "mkl_vml_def.2.dll") |
                  ForEach-Object { Join-Path $MklBin $_ }
        $files += @("libiomp5md.dll", "libmmd.dll", "svml_dispmd.dll") | ForEach-Object { Join-Path $CmpBin $_ }
        $files += Join-Path $TbbBin "tbb12.dll"
        $files += @("wxbase32u_vc_x64_custom.dll", "wxmsw32u_core_vc_x64_custom.dll", "pcre2-16.dll",
                    "libpng16.dll", "jpeg62.dll", "tiff.dll", "liblzma.dll", "zlib1.dll") |
                  ForEach-Object { Join-Path $WxBin $_ }
        return @{ Config = $cfg; Files = $files }
    } else {
        $cfg = "Release_Static_public"
        $files = @(
            (Join-Path $MeRoot "mbs\freedyn_c_interface\freedyn_c_api\bin\$cfg\freedyn_mt.dll"),
            $logo
        ) + (Get-KernelDlls $cfg "Release_Static")
        $files += Join-Path $CmpBin "libiomp5md.dll"
        $files += Join-Path $TbbBin "tbb12.dll"
        return @{ Config = $cfg; Files = $files }
    }
}

# ---------------------------------------------------------------------------
# 0. Pre-flight checks
# ---------------------------------------------------------------------------
Step "Pre-flight checks"

if (-not (Test-Path (Join-Path $MeRoot "mbs"))) { Die "me repository not found at $MeRoot." }

$meCommit = (git -C $MeRoot rev-parse --short HEAD 2>$null)
if (-not $meCommit) { $meCommit = "unknown" }
$meDirty = (git -C $MeRoot status --porcelain --untracked-files=no 2>$null)
Write-Host "  me: $MeRoot @ $meCommit$(if ($meDirty) { ' (uncommitted changes!)' })"
if ($meDirty) {
    Write-Warning "me has uncommitted changes - the binaries may not match any commit."
}

$variants = if ($Variant -eq "Both") { @("MD", "MT") } else { @($Variant) }

# Resolve and check all sources before touching anything
$plan = @{}
$missing = @()
foreach ($v in $variants) {
    $src = Get-SourceFiles $v
    foreach ($f in $src.Files) {
        if (-not (Test-Path $f)) { $missing += "[$v] $f" }
    }
    $plan[$v] = $src
}
if ($missing) {
    Die ("Missing source files (build the configuration in me first):`n  " + ($missing -join "`n  "))
}

# ---------------------------------------------------------------------------
# 1. Copy binaries
# ---------------------------------------------------------------------------
foreach ($v in $variants) {
    $src = $plan[$v]
    $target = Join-Path $RepoRoot "bin\x64_$v"
    Step "x64_$v <- $($src.Config)$(if ($DryRun) { ' (DryRun)' })"

    # The API DLL is built last in a full build of the configuration. A kernel DLL
    # newer than the API DLL stems from a later (e.g. development) build and may
    # not be ABI compatible -> refuse to mix.
    $ownBuild = $src.Files | Where-Object { $_.StartsWith($MeRoot, [StringComparison]::OrdinalIgnoreCase) -and $_ -notlike "*.png" }
    $apiDll = $ownBuild | Where-Object { $_ -like "*\freedyn.dll" -or $_ -like "*\freedyn_mt.dll" }
    $apiTime = (Get-Item $apiDll).LastWriteTime
    $times = $ownBuild | ForEach-Object { (Get-Item $_).LastWriteTime }
    $newest = ($times | Measure-Object -Maximum).Maximum
    $oldest = ($times | Measure-Object -Minimum).Minimum
    Write-Host ("  API DLL built {0:yyyy-MM-dd HH:mm}" -f $apiTime)
    $tooNew = $ownBuild | Where-Object { (Get-Item $_).LastWriteTime -gt $apiTime.AddMinutes(10) }
    if ($tooNew) {
        $list = $tooNew | ForEach-Object { "{0:yyyy-MM-dd HH:mm}  {1}" -f (Get-Item $_).LastWriteTime, $_ }
        Die ("Build outputs newer than the API DLL of $($src.Config) - rebuild the whole configuration in me:`n    " + ($list -join "`n    "))
    }

    if ($DryRun) {
        $src.Files | ForEach-Object { Write-Host "  would copy $_" }
        continue
    }

    New-Item -ItemType Directory -Path $target -Force | Out-Null
    if (-not $NoClean) {
        Get-ChildItem $target -File | Remove-Item -Force
    }
    foreach ($f in $src.Files) {
        Copy-Item $f $target -Force
    }

    $info = @(
        "FreeDyn binaries x64_$v",
        "me configuration: $($src.Config)",
        "me commit:        $meCommit$(if ($meDirty) { ' (with uncommitted changes)' })",
        ("collected:        {0:yyyy-MM-dd HH:mm}" -f (Get-Date)),
        ("build outputs:    {0:yyyy-MM-dd HH:mm} .. {1:yyyy-MM-dd HH:mm}" -f $oldest, $newest)
    )
    Set-Content -Path (Join-Path $target "BUILD_INFO.txt") -Value $info -Encoding ASCII
    Write-Host "  copied $($src.Files.Count) files to $target"
}

# ---------------------------------------------------------------------------
# 2. C-API header
# ---------------------------------------------------------------------------
if (-not $SkipHeader) {
    $hdrSrc = Join-Path $MeRoot "mbs\freedyn_c_interface\freedyn_c_api\hdr\freedyn_c_api.h"
    $hdrDst = Join-Path $RepoRoot "include\freedyn\freedyn_c_api.h"
    Step "C-API header"
    if ((Get-FileHash $hdrSrc).Hash -eq (Get-FileHash $hdrDst).Hash) {
        Write-Host "  include/freedyn/freedyn_c_api.h is up to date."
    } elseif ($DryRun) {
        Write-Host "  would update include/freedyn/freedyn_c_api.h (differs from me)" -ForegroundColor Yellow
    } else {
        Copy-Item $hdrSrc $hdrDst -Force
        Write-Warning "  include/freedyn/freedyn_c_api.h updated from me - review and commit it (bindings may need updates)."
    }
}

Step "Done$(if ($DryRun) { ' (DryRun - nothing changed)' })"
