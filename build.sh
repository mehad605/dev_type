#!/bin/bash
# Linux build script for dev_type
# Run this file to build the portable executable and AppImage

echo "========================================"
echo "  Dev Type - Linux Build"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found!"
    echo "Please install Python and try again."
    exit 1
fi

# Check if uv is available (preferred)
if command -v uv &> /dev/null; then
    echo "Using uv to run build script..."
    uv run python build.py --linux --appimage --clean
else
    echo "Using python to run build script..."
    # Ensure dependencies are installed
    python3 -m pip install . pyinstaller
    python3 build.py --linux --appimage --clean
fi

echo ""
echo "========================================"
echo "  Build Process Complete!"
echo "========================================"
echo ""
echo "Check the dist/ folder for your build."
echo ""
