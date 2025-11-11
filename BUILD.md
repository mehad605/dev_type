# Building Portable Executables

This guide explains how to build portable executables for Dev Type.

## Quick Start

### Windows
Simply double-click `build.bat` or run:
```bash
python build.py --windows --clean
```

### Linux
Run the build script:
```bash
chmod +x build.sh
./build.sh
```

Or directly:
```bash
python build.py --linux --clean
```

## What Gets Built

### Windows
- **dev_type.exe** - Single-file portable executable
- No installation needed
- Runs from any location
- Creates `Dev_Type_Data/` folder automatically

### Linux
- **dev_type** - Executable binary
- Can be packaged into AppImage
- Portable and self-contained
- Creates `Dev_Type_Data/` folder automatically

## Portable Data Directory

When you run the executable, it automatically creates a `Dev_Type_Data/` folder in the same directory:

```
dev_type.exe          (or dev_type.AppImage)
Dev_Type_Data/
  ├── typing_stats.db   (your statistics and settings)
  ├── ghosts/           (your best session replays)
  ├── settings/         (future: custom exports)
  └── logs/             (future: app logs)
```

### Why This Matters

1. **Easy Updates**: Just replace the `.exe` or `.AppImage`, keep the `Dev_Type_Data/` folder
2. **Portable**: Copy the folder to USB drive, cloud storage, etc.
3. **No Data Loss**: Your progress is always preserved
4. **Multi-Version**: Run different versions side-by-side with separate Dev_Type_Data folders

## Build Requirements

The build script will check for these automatically:

- **Python 3.13+** (already installed if you're developing)
- **PyInstaller** (auto-installed via `uv sync`)
- **Pillow** (auto-installed via `uv sync`)

All dependencies are listed in `pyproject.toml`.

## Build Options

```bash
# Build for current platform
python build.py

# Build for Windows
python build.py --windows

# Build for Linux
python build.py --linux

# Clean build directories first (recommended)
python build.py --clean

# Combine options
python build.py --windows --clean
```

## Creating AppImage (Linux)

After building the Linux executable, follow these steps:

1. **Download appimagetool:**
   ```bash
   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage
   ```

2. **The build script creates the AppDir structure automatically** (if you choose yes)

3. **Create the AppImage:**
   ```bash
   ./appimagetool-x86_64.AppImage AppDir dev_type.AppImage
   ```

4. **Make it executable:**
   ```bash
   chmod +x dev_type.AppImage
   ```

5. **Run it:**
   ```bash
   ./dev_type.AppImage
   ```

## Distribution

### What to Include

**Minimum (first-time users):**
- `dev_type.exe` (or `dev_type.AppImage`)

**Recommended:**
- `dev_type.exe` (or `dev_type.AppImage`)
- `README.md` - User documentation
- `LICENSE` - License information

**Do NOT include:**
- `Dev_Type_Data/` folder (contains user-specific data)
- Build artifacts (`build/`, `dist/`)

### Update Distribution

When you release an update:

1. Build new executable: `python build.py --clean`
2. Users download new `.exe` or `.AppImage`
3. Users replace old executable, keeping `Dev_Type_Data/` folder
4. Launch new version - all data preserved! ✨

## Testing the Build

Before distributing:

1. **Build the executable**
   ```bash
   python build.py --clean
   ```

2. **Copy to a test location**
   ```bash
   mkdir test_portable
   cp dist/dev_type.exe test_portable/  # Windows
   # or
   cp dist/dev_type test_portable/      # Linux
   ```

3. **Run from test location**
   - Verify `Dev_Type_Data/` folder is created
   - Complete a typing session
   - Check that `Dev_Type_Data/typing_stats.db` exists
   - Save a ghost, check `Dev_Type_Data/ghosts/` folder
   - Close and reopen - verify data persists

4. **Test update scenario**
   - Build again (simulate an update)
   - Copy new executable to `test_portable/`
   - Run - verify old data is still there

## Troubleshooting

### "PyInstaller not found"
```bash
uv sync
# or
pip install pyinstaller
```

### "Icon file not found"
```bash
python -m app.generate_icon  # Regenerate PNG icons
python -m app.create_ico     # Create Windows ICO
```

### Build fails with import errors
Check `build.py` and ensure all app modules are in `--hidden-import` list.

### Dev_Type_Data folder not created
- Check `app/portable_data.py` 
- Verify the executable has write permissions
- Run from a location where you have write access

### App doesn't start
- On Windows: Check Windows Defender/antivirus
- On Linux: Ensure executable permission (`chmod +x`)
- Check console output for error messages

## Advanced Configuration

### Custom Icon

1. Edit `app/icon.svg`
2. Regenerate images:
   ```bash
   python -m app.generate_icon
   python -m app.create_ico
   ```
3. Rebuild

### Modify Build Settings

Edit `build.py` to customize:
- `--onefile` vs `--onedir` (single file vs directory)
- `--windowed` vs `--console` (GUI vs console window)
- Hidden imports
- Data files to include

### Size Optimization

The executable is larger because it includes:
- Python interpreter
- PySide6 (Qt framework)
- All app code and dependencies

To reduce size:
- Use `--onedir` mode (faster startup, slightly larger)
- Enable UPX compression (add `--upx-dir` to PyInstaller)
- Remove unused imports from code

## Continuous Integration

To automate builds with GitHub Actions, create `.github/workflows/build.yml`:

```yaml
name: Build Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: python build.py --windows --clean
      - uses: actions/upload-artifact@v3
        with:
          name: dev_type-windows
          path: dist/dev_type.exe

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: python build.py --linux --clean
      - uses: actions/upload-artifact@v3
        with:
          name: dev_type-linux
          path: dist/dev_type
```

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Test on clean Windows machine
- [ ] Test on clean Linux machine
- [ ] Build with `--clean` flag
- [ ] Test data persistence
- [ ] Test update scenario
- [ ] Create GitHub release
- [ ] Upload executables
- [ ] Update documentation

## Support

For build issues, check:
1. This README
2. GitHub Issues
3. PyInstaller documentation: https://pyinstaller.org/
