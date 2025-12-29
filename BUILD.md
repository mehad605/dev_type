# Building Dev Type

This guide explains how to build a standalone executable for Dev Type that can be shared with anyone without requiring Python or any dependencies.

## Quick Start

### Windows
Simply double-click `build.bat` or run:
```powershell
.\build.bat
```

### Linux/macOS
Make the script executable and run:
```bash
chmod +x build.sh
./build.sh
```

### Manual Build
```bash
# Using uv (recommended)
uv run python build.py --windows --clean

# Or with regular Python
python build.py --windows --clean
```

## Build Output

After a successful build, you'll find:
- **Windows**: `dist/dev_type.exe` (~57 MB)
- **Linux**: `dist/dev_type` (executable)

The executable is **completely standalone** and includes:
- All Python dependencies (PySide6, Pillow, etc.)
- Application code and resources
- Icons and sound files
- No external dependencies required!

## Distribution

To share the application:
1. Locate the executable in the `dist/` folder
2. Send just the `.exe` (Windows) or binary (Linux) file
3. Recipients can run it immediately - **no Python installation needed**
4. The app will create a `Dev_Type_Data/` folder on first run for:
   - User settings
   - Statistics database
   - Ghost recordings
   - Custom sounds
   - Downloaded language icons
   - Log files

## Build Requirements

The build machine needs:
- Python 3.8+ installed
- PyInstaller (`uv add pyinstaller` or `pip install pyinstaller`)
- All project dependencies (`uv sync` or `pip install -r requirements.txt`)

**End users need NOTHING** - the executable is fully self-contained!

## Build Options

```bash
python build.py --windows     # Build for Windows
python build.py --linux       # Build for Linux
python build.py --clean       # Clean build directories first
python build.py --all         # Build for all platforms (current OS)
```

## Build Configuration

### PyInstaller Spec File
The build uses `dev_type.spec` which configures:
- **Single-file executable**: Everything packed into one `.exe`
- **No console window**: GUI-only application
- **Icon embedding**: Windows shows the app icon
- **Version information**: File properties on Windows
- **Hidden imports**: Ensures all modules are included
- **Asset bundling**: Icons, sounds, and resources

### Key Features
- ✅ **UPX disabled**: Prevents antivirus false positives
- ✅ **All app modules included**: Comprehensive hidden imports
- ✅ **Portable data directory**: Automatically created on first run
- ✅ **High-quality icon**: Multi-size ICO for Windows
- ✅ **Sound files bundled**: All audio feedback included

## Troubleshooting

### "PyInstaller not found"
Install it:
```bash
uv add pyinstaller
# or
pip install pyinstaller
```

### "Missing assets"
Generate the icon files:
```bash
uv run python app/generate_icon.py
```

### "Module not found" at runtime
Add the missing module to hidden imports in:
- `build.py` (in the `cmd.extend([...])` sections)
- `dev_type.spec` (in the `hiddenimports=[...]` list)

### Antivirus Flags the Executable
This is a common false positive with PyInstaller. The build already:
- Disables UPX compression (major cause of false positives)
- Includes version information
- Uses a legitimate code structure

If needed, submit the file to your antivirus vendor as a false positive.

### Large Executable Size
The 57 MB size includes:
- PySide6 Qt framework (~40 MB)
- Python runtime (~10 MB)
- Application code and assets (~7 MB)

This is normal for Qt-based applications. The single-file approach trades size for convenience.

## Platform-Specific Notes

### Windows
- Creates `dev_type.exe` with embedded icon
- Includes version information for file properties
- No console window appears
- Icon cache is cleared after build (developer-only)

### Linux
- Creates `dev_type` executable
- Can be packaged into AppImage (see `build.sh`)
- Uses PNG icon format
- May require `chmod +x` before distribution

### macOS
- Build process similar to Linux (not yet fully tested)
- Requires additional work for `.app` bundle
- May need code signing for Gatekeeper

## Updating the Application

To release a new version:
1. Update version in `version_info.txt`
2. Run `python app/generate_icon.py` if icon changed
3. Run the build script
4. Test the executable thoroughly
5. Distribute the new `.exe` file

Users can simply replace the old executable with the new one. Their data folder (`Dev_Type_Data/`) will be preserved.

## Advanced: Manual PyInstaller Usage

If you need more control:
```bash
pyinstaller dev_type.spec
```

Or build from scratch:
```bash
pyinstaller --name=dev_type \
  --onefile \
  --windowed \
  --icon=assets/icon.ico \
  --version-file=version_info.txt \
  --add-data="assets/sounds;assets/sounds" \
  --hidden-import=app.ui_main \
  --noupx \
  run_app.py
```

## Continuous Integration

For automated builds:
```yaml
# GitHub Actions example
- name: Build executable
  run: |
    pip install pyinstaller
    python build.py --windows --clean
    
- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: dev-type-windows
    path: dist/dev_type.exe
```

## Build Verification Checklist

Before distributing:
- [ ] Executable launches without errors
- [ ] All UI elements render correctly
- [ ] Typing functionality works
- [ ] Sound plays properly
- [ ] File scanning works
- [ ] Ghost recordings save/load
- [ ] Settings persist across restarts
- [ ] Icons display correctly
- [ ] Theme switching works
- [ ] Statistics tracking functions
- [ ] Data folder creates automatically
- [ ] Runs on a clean machine without Python

## License Considerations

The built executable includes:
- **PySide6**: LGPL license (dynamic linking okay)
- **Pillow**: PIL License (permissive)
- **PyInstaller**: GPL + exception for distribution

You can freely distribute the compiled executable under these terms.
