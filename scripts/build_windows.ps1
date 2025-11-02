# Windows Build Script for Offline Python Exam System
# Packages the exam runner into a single-file executable for Windows
#
# Prerequisites:
#   - Python 3.11 or higher installed
#   - Network access for initial dependency download (can be done offline with vendor/ directory)
#
# Usage:
#   .\build_windows.ps1
#   .\build_windows.ps1 -OutputPath "C:\MyExams"
#   .\build_windows.ps1 -Clean -OutputPath "..\deploy"
#
# Output:
#   exam.exe - Single-file Windows executable (created in OutputPath, default: project root)

param(
    [switch]$Clean = $false,
    [switch]$Offline = $false,
    [string]$OutputPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Offline Python Exam System - Windows Build" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$VENV_DIR = ".venv-build"
$PYTHON_MIN_VERSION = "3.10"
$EXE_NAME = "exam.exe"
$BUILD_DIR = "build"

# Resolve and create output directory
$OutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    Write-Host "Created output directory: $OutputPath" -ForegroundColor Green
}
Write-Host "Output directory: $OutputPath" -ForegroundColor Cyan
Write-Host ""

# Clean previous builds if requested
if ($Clean) {
    Write-Host "[1/6] Cleaning previous build artifacts..." -ForegroundColor Yellow
    
    # Remove built executable
    if (Test-Path $EXE_NAME) {
        Remove-Item -Force $EXE_NAME
        Write-Host "  - Removed $EXE_NAME" -ForegroundColor Gray
    }
    
    # Remove old dist/ directory if it exists
    if (Test-Path "dist") {
        Remove-Item -Recurse -Force "dist"
        Write-Host "  - Removed dist/" -ForegroundColor Gray
    }
    
    # Remove build directory
    if (Test-Path $BUILD_DIR) {
        Remove-Item -Recurse -Force $BUILD_DIR
        Write-Host "  - Removed $BUILD_DIR" -ForegroundColor Gray
    }
    
    # Remove virtual environment
    if (Test-Path $VENV_DIR) {
        Remove-Item -Recurse -Force $VENV_DIR
        Write-Host "  - Removed $VENV_DIR" -ForegroundColor Gray
    }
    
    Write-Host "  Clean complete." -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping clean (use -Clean to remove old builds)" -ForegroundColor Gray
}

# Check Python installation
Write-Host "[2/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
    
    # Extract version number and validate
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$matches[1]
        $minVersion = [version]$PYTHON_MIN_VERSION
        if ($version -lt $minVersion) {
            Write-Host "  ERROR: Python $PYTHON_MIN_VERSION or higher required" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "  ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python $PYTHON_MIN_VERSION or higher from python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "[3/6] Setting up build environment..." -ForegroundColor Yellow
if (-not (Test-Path $VENV_DIR)) {
    python -m venv $VENV_DIR
    Write-Host "  - Created virtual environment: $VENV_DIR" -ForegroundColor Green
} else {
    Write-Host "  - Using existing virtual environment: $VENV_DIR" -ForegroundColor Gray
}

# Activate virtual environment
$activateScript = Join-Path $VENV_DIR "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "  - Activated virtual environment" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Failed to find activation script" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
if ($Offline) {
    if (Test-Path "vendor") {
        & pip install --no-index --find-links vendor -r requirements.txt
        & pip install --no-index --find-links vendor pyinstaller
        Write-Host "  - Installed from vendor/ directory (offline mode)" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Offline mode requested but vendor/ directory not found" -ForegroundColor Red
        exit 1
    }
} else {
    & python.exe -m pip install --upgrade pip
    & python.exe -m pip install -r requirements.txt
    & python.exe -m pip install pyinstaller>=6.0.0
    Write-Host "  - Installed from PyPI (online mode)" -ForegroundColor Green
}

# Verify PyInstaller
$pyinstallerVersion = & pyinstaller --version 2>&1
Write-Host "  Using PyInstaller: $pyinstallerVersion" -ForegroundColor Gray

# Build executable
Write-Host "[5/6] Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host "  This may take several minutes..." -ForegroundColor Gray
& pyinstaller scripts\exam.spec --clean --distpath $OutputPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "  - Build successful" -ForegroundColor Green
} else {
    Write-Host "  ERROR: PyInstaller build failed" -ForegroundColor Red
    exit 1
}

# Verify output
Write-Host "[6/6] Verifying build output..." -ForegroundColor Yellow
$exePath = Join-Path $OutputPath $EXE_NAME
if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "  - Executable created: $exePath" -ForegroundColor Green
    Write-Host "  - Size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Gray
    
    # Quick smoke test
    Write-Host "  - Running smoke test..." -ForegroundColor Gray
    $testOutput = & $exePath --help 2>&1
    if ($testOutput -match "usage:" -or $testOutput -match "Offline Python Exam") {
        Write-Host "  - Smoke test passed" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Smoke test produced unexpected output" -ForegroundColor Yellow
        Write-Host "  Output: $testOutput" -ForegroundColor Gray
    }
} else {
    Write-Host "  ERROR: Executable not found at expected location" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  BUILD COMPLETE" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Executable location: $exePath" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test the executable: $exePath --help" -ForegroundColor Gray
Write-Host "  2. Copy banks\ directory to: $OutputPath" -ForegroundColor Gray
Write-Host "  3. Deploy to exam machines" -ForegroundColor Gray
Write-Host ""
Write-Host "TIP: The executable will find banks\ next to itself, so you can run it from anywhere!" -ForegroundColor Cyan
Write-Host ""

