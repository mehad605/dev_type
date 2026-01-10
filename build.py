"""
Build script for creating portable executables.

This script creates:
- Windows: dev_type.exe (single-file executable)
- Linux: dev_type (executable that can be packaged into AppImage)

Usage:
    python build.py              # Build for current platform
    python build.py --windows    # Build Windows exe
    python build.py --linux      # Build Linux executable
    python build.py --all        # Build for all platforms (if possible)
    python build.py --clean      # Clean build directories first

Requirements:
    pip install pyinstaller
"""
import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


class Builder:
    """Handles building portable executables."""
    
    def __init__(self, clean: bool = False):
        self.root = Path(__file__).parent
        self.build_dir = self.root / "build"
        self.dist_dir = self.root / "dist"
        self.clean_first = clean
        
        # Detect platform
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_linux = self.system == "linux"
        self.is_mac = self.system == "darwin"
    
    def clean(self):
        """Remove build artifacts."""
        print("Cleaning build directories...")
        
        dirs_to_clean = [self.build_dir, self.dist_dir, self.root / "__pycache__"]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed {dir_path}")
        
        print("[OK] Clean complete\n")
    
    def check_pyinstaller(self):
        """Ensure PyInstaller is installed."""
        try:
            import PyInstaller
            print(f"[OK] PyInstaller {PyInstaller.__version__} found")
            return True
        except ImportError:
            print("[ERROR] PyInstaller not found!")
            print("   Install it with: pip install pyinstaller")
            return False
    
    def check_assets(self):
        """Verify required asset files exist."""
        print("Checking required assets...")
        
        required_files = [
            self.root / "assets" / "icon.png",
            self.root / "assets" / "sounds",
        ]
        
        if self.is_windows:
            required_files.append(self.root / "assets" / "icon.ico")
        
        missing = []
        for file_path in required_files:
            if not file_path.exists():
                missing.append(file_path)
                print(f"   [MISSING] Missing: {file_path}")
            else:
                print(f"   [OK] Found: {file_path.name}")
        
        if missing:
            print("\n[ERROR] Some required assets are missing!")
            return False
        
        print("[OK] All required assets found\n")
        return True
    
    def get_icon_path(self) -> str:
        """Get the appropriate icon file for the platform."""
        if self.is_windows:
            # Windows needs .ico file
            ico_path = self.root / "assets" / "icon.ico"
            if not ico_path.exists():
                print("[WARN] Windows .ico file not found, will use .png")
                return str(self.root / "assets" / "icon.png")
            return str(ico_path)
        else:
            # Linux/Mac can use PNG
            return str(self.root / "assets" / "icon.png")
    
    def build_windows(self):
        """Build Windows executable."""
        print("Building Windows executable...\n")
        
        icon_path = self.get_icon_path()
        version_file = self.root / "version_info.txt"
        
        # Use main.py as entry point (contains splash screen initialization)
        entry_script = self.root / "main.py"
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--name=dev_type",
            "--onefile",  # Single executable file
            "--windowed",  # No console window
            f"--icon={icon_path}",
            # NOTE: No --splash argument - we use custom Tkinter splash instead
            # This allows users to customize splash.png in Dev_Type_Data folder
        ]
        
        # Add version info for Windows
        if version_file.exists():
            cmd.append(f"--version-file={version_file}")
        
        # Add data files and other options
        cmd.extend([
            # Add data files
            "--add-data=assets/icon.svg;assets",
            "--add-data=assets/icon.png;assets",
            "--add-data=assets/icon.ico;assets",
            "--add-data=assets/sounds;assets/sounds",  # Include sounds directory
            
            # Hidden imports that PyInstaller might miss
            "--hidden-import=PySide6.QtSvg",
            "--hidden-import=PySide6.QtSvgWidgets",
            "--hidden-import=PySide6.QtMultimedia",
            "--hidden-import=PySide6.QtNetwork",  # Often needed for local socket/event loop internals
            
            # Exclude heavy unused libraries to reduce size
            "--exclude-module=matplotlib",
            "--exclude-module=numpy",
            "--exclude-module=pandas",
            "--exclude-module=scipy",
            "--exclude-module=IPython",
            "--exclude-module=PIL", # We use PySide6 for images, unless Pillow is explicitly needed
            
            "--hidden-import=_tkinter",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.font",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=app.portable_data",
            "--hidden-import=app.ghost_manager",
            "--hidden-import=app.stats_db",
            "--hidden-import=app.settings",
            "--hidden-import=app.themes",
            "--hidden-import=app.typing_engine",
            "--hidden-import=app.typing_area",
            "--hidden-import=app.sound_manager",
            "--hidden-import=app.sound_profile_editor",
            "--hidden-import=app.sound_volume_widget",
            "--hidden-import=app.icon_manager",
            "--hidden-import=app.language_cache",
            "--hidden-import=app.file_scanner",
            "--hidden-import=app.file_tree",
            "--hidden-import=app.editor_tab",
            "--hidden-import=app.history_tab",
            "--hidden-import=app.languages_tab",
            "--hidden-import=app.session_result_dialog",
            "--hidden-import=app.ghost_replay_widget",
            "--hidden-import=app.stats_display",
            "--hidden-import=app.progress_bar_widget",
            "--hidden-import=app.instant_splash",
            
            # Disable UPX compression to avoid antivirus false positives
            "--noupx",
            
            # Clean build
            "--clean",
            
            # Entry point
            str(entry_script),
        ])
        
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, check=True, cwd=self.root)
            print("\n[SUCCESS] Windows build complete!")
            print(f"   Executable: {self.dist_dir / 'dev_type.exe'}")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Build failed with error code {e.returncode}")
            
            return False
    
    def build_linux(self, appimage: bool = False):
        """Build Linux executable and optionally package as AppImage."""
        print("Building Linux executable...\n")
        
        icon_path = self.get_icon_path()
        
        # Create a temporary entry point script
        entry_script = self.root / "run_app.py"
        entry_script.write_text("""#!/usr/bin/env python
if __name__ == "__main__":
    from app.ui_main import run_app
    run_app()
""")
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--name=dev_type",
            "--onefile" if not appimage else "--onedir",  # onedir is better for AppImage
            f"--icon={icon_path}",
            
            # Add data files
            "--add-data=assets/icon.svg:assets",
            "--add-data=assets/icon.png:assets",
            "--add-data=assets/sounds:assets/sounds",  # Include sounds directory
            
            # Hidden imports
            "--hidden-import=PySide6.QtSvg",
            "--hidden-import=PySide6.QtSvgWidgets",
            "--hidden-import=PySide6.QtMultimedia",
            "--hidden-import=app.portable_data",
            "--hidden-import=app.ghost_manager",
            "--hidden-import=app.stats_db",
            "--hidden-import=app.settings",
            "--hidden-import=app.themes",
            "--hidden-import=app.typing_engine",
            "--hidden-import=app.typing_area",
            "--hidden-import=app.sound_manager",
            "--hidden-import=app.sound_profile_editor",
            "--hidden-import=app.sound_volume_widget",
            "--hidden-import=app.icon_manager",
            "--hidden-import=app.language_cache",
            "--hidden-import=app.file_scanner",
            "--hidden-import=app.file_tree",
            "--hidden-import=app.editor_tab",
            "--hidden-import=app.history_tab",
            "--hidden-import=app.languages_tab",
            "--hidden-import=app.session_result_dialog",
            "--hidden-import=app.ghost_replay_widget",
            "--hidden-import=app.stats_display",
            "--hidden-import=app.progress_bar_widget",
            "--hidden-import=app.instant_splash",
            "--hidden-import=_tkinter",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.font",
            "--hidden-import=tkinter.ttk",
            
            # Disable UPX compression to avoid antivirus false positives
            "--noupx",
            
            # Clean build
            "--clean",
            
            # Entry point
            str(entry_script)
        ]
        
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, check=True, cwd=self.root)
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            if appimage:
                return self.create_appimage()
            
            print("\n[SUCCESS] Linux build complete!")
            print(f"   Executable: {self.dist_dir / 'dev_type'}")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Build failed with error code {e.returncode}")
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            return False

    def create_appimage(self):
        """Package the dist/dev_type directory into an AppImage."""
        print("\nPackaging as AppImage...")
        
        appdir = self.root / "AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        
        # 1. Create structure
        (appdir / "usr" / "bin").mkdir(parents=True)
        
        # 2. Copy PyInstaller output
        source_dir = self.dist_dir / "dev_type"
        if not source_dir.exists():
            # Fallback for --onefile output
            source_bin = self.dist_dir / "dev_type"
            if not source_bin.exists():
                print("[ERROR] Could not find PyInstaller output!")
                return False
            shutil.copy2(source_bin, appdir / "usr" / "bin" / "dev_type")
        else:
            # Copy entire onedir contents to usr/bin
            for item in source_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, appdir / "usr" / "bin" / item.name)
                else:
                    shutil.copy2(item, appdir / "usr" / "bin" / item.name)
        
        # 3. Create Desktop file
        desktop_content = """[Desktop Entry]
Name=Dev Type
Exec=dev_type
Icon=dev_type
Type=Application
Categories=Development;Education;
Comment=Master touch typing while coding
Terminal=false
"""
        (appdir / "dev_type.desktop").write_text(desktop_content)
        
        # 4. Copy Icon
        icon_source = self.root / "assets" / "icon.png"
        shutil.copy2(icon_source, appdir / "dev_type.png")
        
        # 5. Create AppRun script
        apprun_content = """#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/dev_type" "$@"
"""
        apprun_file = appdir / "AppRun"
        apprun_file.write_text(apprun_content)
        try:
            subprocess.run(["chmod", "+x", str(apprun_file)], check=False)
        except:
            pass # Might fail on Windows
        
        # 6. Call appimagetool if available
        appimagetool = shutil.which("appimagetool") or shutil.which("appimagetool-x86_64.AppImage")
        
        if not appimagetool:
            print("\n[INFO] AppDir structure created at ./AppDir")
            print("To finish AppImage creation, download appimagetool and run:")
            print("   ./appimagetool AppDir dev_type.AppImage")
            return True
        
        try:
            print(f"Running {appimagetool}...")
            env = os.environ.copy()
            if "ARCH" not in env:
                import platform
                machine = platform.machine().lower()
                if "x86_64" in machine or "amd64" in machine:
                    env["ARCH"] = "x86_64"
                elif "arm64" in machine or "aarch64" in machine:
                    env["ARCH"] = "aarch64"
                else:
                    env["ARCH"] = machine
            
            subprocess.run([appimagetool, str(appdir), str(self.dist_dir / "dev_type.AppImage")], 
                           check=True, env=env)
            print(f"\n[SUCCESS] AppImage created: {self.dist_dir / 'dev_type.AppImage'}")
            return True
        except Exception as e:
            print(f"\n[ERROR] AppImage packaging failed: {e}")
            return False
    
    def build(self, target: str = "current", appimage: bool = False):
        """Build for specified target platform."""
        if self.clean_first:
            self.clean()
        
        if not self.check_pyinstaller():
            return False
        
        if not self.check_assets():
            return False
        
        success = True
        
        if target == "current":
            if self.is_windows:
                success = self.build_windows()
            elif self.is_linux:
                success = self.build_linux(appimage=appimage)
            elif self.is_mac:
                print("[WARN] macOS build not yet implemented")
                print("   Linux build process should work with minor adjustments")
                success = False
            else:
                print(f"[ERROR] Unsupported platform: {self.system}")
                success = False
        
        elif target == "windows":
            success = self.build_windows()
        
        elif target == "linux":
            success = self.build_linux(appimage=appimage)
        
        elif target == "all":
            print("Building for all platforms...\n")
            if self.is_windows:
                success = self.build_windows()
            elif self.is_linux:
                success = self.build_linux(appimage=appimage)
            else:
                print("[WARN] Building for multiple platforms from this OS not supported")
                success = False
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build portable executables for dev_type")
    parser.add_argument("--windows", action="store_true", help="Build Windows executable")
    parser.add_argument("--linux", action="store_true", help="Build Linux executable")
    parser.add_argument("--appimage", action="store_true", help="Package Linux build as AppImage")
    parser.add_argument("--all", action="store_true", help="Build for all platforms")
    parser.add_argument("--clean", action="store_true", help="Clean build directories first")
    
    args = parser.parse_args()
    
    # Determine target
    if args.windows:
        target = "windows"
    elif args.linux:
        target = "linux"
    elif args.all:
        target = "all"
    else:
        target = "current"
    
    builder = Builder(clean=args.clean)
    
    print("=" * 60)
    print("  Dev Type - Portable Build System")
    print("=" * 60)
    print()
    
    success = builder.build(target, appimage=args.appimage)
    
    if success:
        print("\n" + "=" * 60)
        print("  [SUCCESS] BUILD SUCCESSFUL")
        print("=" * 60)
        print("\nNext steps:")
        print("   1. Test the executable in dist/")
        print("   2. The 'data' folder will be created automatically on first run")
        print("   3. To update: just replace the executable, keep the data folder")
        return 0
    else:
        print("\n" + "=" * 60)
        print("  [FAILED] BUILD FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
