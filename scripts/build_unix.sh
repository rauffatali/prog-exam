#!/usr/bin/env bash
# Unix Build Script for Offline Python Exam System
# Packages the exam runner into a single-file executable for macOS and Linux
#
# Prerequisites:
#   - Python 3.11 or higher installed
#   - Network access for initial dependency download (can be done offline with vendor/ directory)
#
# Usage:
#   ./build_unix.sh
#   ./build_unix.sh --output /path/to/output
#   ./build_unix.sh --clean --output ../deploy
#
# Output:
#   exam - Single-file Unix executable (created in --output path, default: project root)

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
VENV_DIR=".venv-build"
PYTHON_MIN_VERSION="3.10"
EXE_NAME="exam"
BUILD_DIR="build"
CLEAN=0
OFFLINE=0
OUTPUT_PATH="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=1
            shift
            ;;
        --offline)
            OFFLINE=1
            shift
            ;;
        --output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--clean] [--offline] [--output PATH]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  Offline Python Exam System - Unix Build${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Resolve and create output directory
OUTPUT_PATH=$(realpath -m "$OUTPUT_PATH")
if [ ! -d "$OUTPUT_PATH" ]; then
    mkdir -p "$OUTPUT_PATH"
    echo -e "${GREEN}Created output directory: $OUTPUT_PATH${NC}"
fi
echo -e "${CYAN}Output directory: $OUTPUT_PATH${NC}"
echo ""

# Clean previous builds if requested
if [ $CLEAN -eq 1 ]; then
    echo -e "${YELLOW}[1/6] Cleaning previous build artifacts...${NC}"
    
    # Remove built executable
    [ -f "$EXE_NAME" ] && rm -f "$EXE_NAME" && echo -e "  ${GRAY}- Removed $EXE_NAME${NC}"
    
    # Remove old dist/ directory if it exists
    [ -d "dist" ] && rm -rf "dist" && echo -e "  ${GRAY}- Removed dist/${NC}"
    
    # Remove build directory
    [ -d "$BUILD_DIR" ] && rm -rf "$BUILD_DIR" && echo -e "  ${GRAY}- Removed $BUILD_DIR${NC}"
    
    # Remove virtual environment
    [ -d "$VENV_DIR" ] && rm -rf "$VENV_DIR" && echo -e "  ${GRAY}- Removed $VENV_DIR${NC}"
    
    echo -e "  ${GREEN}Clean complete.${NC}"
else
    echo -e "${GRAY}[1/6] Skipping clean (use --clean to remove old builds)${NC}"
fi

# Check Python installation
echo -e "${YELLOW}[2/6] Checking Python installation...${NC}"

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "  ${RED}ERROR: Python not found in PATH${NC}"
    echo -e "  ${RED}Please install Python $PYTHON_MIN_VERSION or higher${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "  ${GREEN}Found: Python $PYTHON_VERSION${NC}"

# Validate version
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
REQUIRED_MAJOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f1)
REQUIRED_MINOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt "$REQUIRED_MAJOR" ] || ([ "$PYTHON_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PYTHON_MINOR" -lt "$REQUIRED_MINOR" ]); then
    echo -e "  ${RED}ERROR: Python $PYTHON_MIN_VERSION or higher required${NC}"
    echo -e "  ${RED}Found: Python $PYTHON_VERSION${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${YELLOW}[3/6] Setting up build environment...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "  ${GREEN}- Created virtual environment: $VENV_DIR${NC}"
else
    echo -e "  ${GRAY}- Using existing virtual environment: $VENV_DIR${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo -e "  ${GREEN}- Activated virtual environment${NC}"

# Install dependencies
echo -e "${YELLOW}[4/6] Installing dependencies...${NC}"
if [ $OFFLINE -eq 1 ]; then
    if [ -d "vendor" ]; then
        pip install --no-index --find-links vendor -r requirements.txt
        pip install --no-index --find-links vendor pyinstaller
        echo -e "  ${GREEN}- Installed from vendor/ directory (offline mode)${NC}"
    else
        echo -e "  ${RED}ERROR: Offline mode requested but vendor/ directory not found${NC}"
        exit 1
    fi
else
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install "pyinstaller>=6.0.0"
    echo -e "  ${GREEN}- Installed from PyPI (online mode)${NC}"
fi

# Verify PyInstaller
PYINSTALLER_VERSION=$(pyinstaller --version 2>&1)
echo -e "  ${GRAY}Using PyInstaller: $PYINSTALLER_VERSION${NC}"

# Build executable
echo -e "${YELLOW}[5/6] Building executable with PyInstaller...${NC}"
echo -e "  ${GRAY}This may take several minutes...${NC}"
pyinstaller scripts/exam.spec --clean --distpath "$OUTPUT_PATH"

echo -e "  ${GREEN}- Build successful${NC}"

# Verify output
echo -e "${YELLOW}[6/6] Verifying build output...${NC}"
EXE_PATH="$OUTPUT_PATH/$EXE_NAME"
if [ -f "$EXE_PATH" ]; then
    EXE_SIZE=$(du -h "$EXE_PATH" | cut -f1)
    echo -e "  ${GREEN}- Executable created: $EXE_PATH${NC}"
    echo -e "  ${GRAY}- Size: $EXE_SIZE${NC}"
    
    # Make executable
    chmod +x "$EXE_PATH"
    echo -e "  ${GRAY}- Set executable permissions${NC}"
    
    # Quick smoke test
    echo -e "  ${GRAY}- Running smoke test...${NC}"
    if "$EXE_PATH" --help 2>&1 | grep -q -E "usage:|Offline Python Exam"; then
        echo -e "  ${GREEN}- Smoke test passed${NC}"
    else
        echo -e "  ${YELLOW}WARNING: Smoke test produced unexpected output${NC}"
    fi
else
    echo -e "  ${RED}ERROR: Executable not found at expected location${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  BUILD COMPLETE${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""
echo -e "${GREEN}Executable location: $EXE_PATH${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  ${GRAY}1. Test the executable: $EXE_PATH --help${NC}"
echo -e "  ${GRAY}2. Copy banks/ directory to: $OUTPUT_PATH${NC}"
echo -e "  ${GRAY}3. Deploy to exam machines${NC}"
echo ""
echo -e "${CYAN}TIP: The executable will find banks/ next to itself, so you can run it from anywhere!${NC}"
echo ""

