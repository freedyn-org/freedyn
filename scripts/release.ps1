<#
.SYNOPSIS
    FreeDyn release script: tag, build wheel, upload it to PyPI,
    create GitHub Release with bin ZIP artifacts.

.PARAMETER Version
    Version string, e.g. "1.0.2" (without leading "v").

.PARAMETER PyPIRepo
    PyPI repository. Use "testpypi" for a dry run, "pypi" for production.
    Default: "testpypi"

.PARAMETER SkipPyPI
    If set, skip the twine upload step.

.PARAMETER SkipGitHub
    If set, skip the GitHub Release creation step.

.EXAMPLE
    .\scripts\release.ps1 -Version 1.0.2 -PyPIRepo testpypi
    .\scripts\release.ps1 -Version 1.0.2 -PyPIRepo pypi
#>
param(
    [Parameter(Mandatory)][string]$Version,
    [string]$PyPIRepo = "testpypi",
    [switch]$SkipPyPI,
    [switch]$SkipGitHub,
    [switch]$DryRun   # Build only - no tag, no upload, no GitHub Release
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Die([string]$msg)  { Write-Error $msg; exit 1 }

# ---------------------------------------------------------------------------
# 0. Pre-flight checks
# ---------------------------------------------------------------------------
Step "Pre-flight checks"

if (-not (git rev-parse --is-inside-work-tree 2>$null)) { Die "Not inside a git repository." }

$dirty = git status --porcelain
if ($dirty) {
    Die "Working tree is dirty. Commit or stash all changes before releasing.`n$dirty"
}

$tag = "v$Version"

if ($DryRun) {
    Write-Host "  DryRun mode: skipping branch check, tag, PyPI upload and GitHub Release." -ForegroundColor Yellow
} else {
    $currentBranch = git rev-parse --abbrev-ref HEAD
    if ($currentBranch -ne "main") {
        Write-Warning "Current branch is '$currentBranch', not 'main'. Continue? [y/N]"
        if ((Read-Host) -notmatch '^[Yy]') { exit 0 }
    }

    $existingTag = git tag -l $tag
    if ($existingTag) { Die "Tag $tag already exists." }

    # Check required tools
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Die "git not found in PATH." }
    if (($PythonExe -eq "python") -and (-not (Get-Command python -ErrorAction SilentlyContinue))) {
        Die "python not found in PATH and no local .venv Python found."
    }
    if (-not $SkipPyPI) {
        if (-not (& $PythonExe -m twine --version 2>$null)) { Die "twine not installed in selected Python env. Run: $PythonExe -m pip install twine" }
    }
    if (-not $SkipGitHub) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { Die "GitHub CLI (gh) not found. Install from https://cli.github.com or use -SkipGitHub." }
    }
}

# ---------------------------------------------------------------------------
# 1. Create and push git tag
# ---------------------------------------------------------------------------
if ($DryRun) {
    Step "Tagging $tag (DryRun - skipped)"
    Write-Host "  Would create tag $tag" -ForegroundColor Yellow
} else {
    Step "Tagging $tag"
    git tag -a $tag -m "Release $tag"
    Write-Host "  Tag created locally."

    $pushTag = Read-Host "  Push tag $tag to origin? [y/N]"
    if ($pushTag -match '^[Yy]') {
        git push origin $tag
        Write-Host "  Tag pushed."
    } else {
        Write-Warning "  Tag not pushed. PyPI and GitHub release steps may fail without it."
    }
}

# ---------------------------------------------------------------------------
# 2. Build
# ---------------------------------------------------------------------------
Step "Building wheel"
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

& $PythonExe -m build --wheel --outdir dist
if ($LASTEXITCODE -ne 0) { Die "Build failed." }

$wheel = Get-ChildItem dist -Filter "*.whl" | Select-Object -First 1
if (-not $wheel) { Die "No wheel found in dist/." }
Write-Host "  Built: $($wheel.Name)"

# ---------------------------------------------------------------------------
# 3. Upload to PyPI
# ---------------------------------------------------------------------------
if ($DryRun) {
    Step "PyPI upload (DryRun - skipped)"
    Write-Host "  Would run: twine check + twine upload for $($wheel.Name) to $PyPIRepo" -ForegroundColor Yellow
} elseif (-not $SkipPyPI) {
    Step "Uploading to $PyPIRepo"
    # twine checks first
    & $PythonExe -m twine check $wheel.FullName
    if ($LASTEXITCODE -ne 0) { Die "twine check failed." }

    if ($PyPIRepo -eq "testpypi") {
        & $PythonExe -m twine upload --repository-url https://test.pypi.org/legacy/ $wheel.FullName
    } else {
        & $PythonExe -m twine upload --repository pypi $wheel.FullName
    }
    if ($LASTEXITCODE -ne 0) { Die "twine upload failed." }
    Write-Host "  Upload complete."
} else {
    Write-Host "  Skipping PyPI upload (-SkipPyPI)."
}

# ---------------------------------------------------------------------------
# 4. Create GitHub Release
# ---------------------------------------------------------------------------
if ($DryRun) {
    Step "GitHub Release (DryRun - skipped)"
    Write-Host "  Would create and upload:" -ForegroundColor Yellow
    Write-Host "    dist/release_assets/FreeDyn-win-x64_MD.zip" -ForegroundColor Yellow
    Write-Host "    dist/release_assets/FreeDyn-win-x64_MT.zip" -ForegroundColor Yellow
} elseif (-not $SkipGitHub) {
    Step "Creating GitHub Release $tag"

    $releaseAssetsDir = Join-Path "dist" "release_assets"
    if (Test-Path $releaseAssetsDir) { Remove-Item $releaseAssetsDir -Recurse -Force }
    New-Item -ItemType Directory -Path $releaseAssetsDir | Out-Null

    $mdZip = Join-Path $releaseAssetsDir "FreeDyn-win-x64_MD.zip"
    $mtZip = Join-Path $releaseAssetsDir "FreeDyn-win-x64_MT.zip"

    if (-not (Test-Path "bin/x64_MD")) { Die "Missing bin/x64_MD folder." }
    if (-not (Test-Path "bin/x64_MT")) { Die "Missing bin/x64_MT folder." }

    Compress-Archive -Path "bin/x64_MD/*" -DestinationPath $mdZip -Force
    Compress-Archive -Path "bin/x64_MT/*" -DestinationPath $mtZip -Force

    $artifacts = @($mdZip, $mtZip)

    $releaseNotes = "Release $tag`n`nSee GETTING_STARTED.md for usage."

    $ghArgs = @(
        "release", "create", $tag,
        "--title", "FreeDyn $tag",
        "--notes", $releaseNotes
    ) + $artifacts

    & gh @ghArgs
    if ($LASTEXITCODE -ne 0) { Die "GitHub release creation failed." }
    Write-Host "  GitHub assets uploaded:" 
    Write-Host "    $(Split-Path $mdZip -Leaf)"
    Write-Host "    $(Split-Path $mtZip -Leaf)"
    Write-Host "  GitHub Release created: https://github.com/freedyn-org/freedyn/releases/tag/$tag"
} else {
    Write-Host "  Skipping GitHub Release (-SkipGitHub)."
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Step "Release $tag complete"
Write-Host "  Wheel:  $($wheel.Name)"
if ($DryRun) {
    Write-Host "  DryRun complete - no tag, no upload, no GitHub Release." -ForegroundColor Yellow
} else {
    if (-not $SkipPyPI)   { Write-Host "  PyPI:   https://pypi.org/project/freedyn/$Version/" }
    if (-not $SkipGitHub) { Write-Host "  GitHub: https://github.com/freedyn-org/freedyn/releases/tag/$tag" }
}
