#!/bin/bash
# Linux/Mac build script for dev_type
# Run this file to build the portable executable

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
    uv run python build.py --linux --clean
else
    echo "Using python to run build script..."
    python3 build.py --linux --clean
fi

echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo ""
echo "Your executable is in the dist/ folder"
echo ""

# Ask if user wants to create AppImage
read -p "Create AppImage? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating AppImage structure..."
    
    # Create AppDir structure
    mkdir -p AppDir/usr/bin
    cp dist/dev_type AppDir/usr/bin/
    cp app/icon.png AppDir/dev_type.png
    
    # Create .desktop file
    cat > AppDir/dev_type.desktop << 'EOF'
[Desktop Entry]
Name=Dev Type
Exec=dev_type
Icon=dev_type
Type=Application
Categories=Development;Education;
Comment=Master touch typing while coding
EOF
    
    chmod +x AppDir/dev_type.desktop
    
    echo ""
    echo "AppDir created! Next steps:"
    echo "1. Download appimagetool:"
    echo "   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    echo "   chmod +x appimagetool-x86_64.AppImage"
    echo ""
    echo "2. Create AppImage:"
    echo "   ./appimagetool-x86_64.AppImage AppDir dev_type.AppImage"
    echo ""
fi
