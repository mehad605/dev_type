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
        print("🧹 Cleaning build directories...")
        
        dirs_to_clean = [self.build_dir, self.dist_dir, self.root / "__pycache__"]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed {dir_path}")
        
        # Remove spec file if it was auto-generated
        spec_file = self.root / "dev_type.spec"
        if spec_file.exists():
            spec_file.unlink()
            print(f"   Removed {spec_file}")
        
        print("✓ Clean complete\n")
    
    def check_pyinstaller(self):
        """Ensure PyInstaller is installed."""
        try:
            import PyInstaller
            print(f"✓ PyInstaller {PyInstaller.__version__} found")
            return True
        except ImportError:
            print("❌ PyInstaller not found!")
            print("   Install it with: pip install pyinstaller")
            return False
    
    def get_icon_path(self) -> str:
        """Get the appropriate icon file for the platform."""
        if self.is_windows:
            # Windows needs .ico file - we'll create it if needed
            ico_path = self.root / "app" / "icon.ico"
            if not ico_path.exists():
                print("⚠️  Windows .ico file not found, will use .png")
                return str(self.root / "app" / "icon.png")
            return str(ico_path)
        else:
            # Linux/Mac can use PNG
            return str(self.root / "app" / "icon.png")
    
    def build_windows(self):
        """Build Windows executable."""
        print("🏗️  Building Windows executable...\n")
        
        icon_path = self.get_icon_path()
        
        # Create a temporary entry point script
        entry_script = self.root / "run_app.py"
        entry_script.write_text("""#!/usr/bin/env python
# Temporary entry point for PyInstaller build
if __name__ == "__main__":
    from app.ui_main import run_app
    run_app()
""")
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--name=dev_type",
            "--onefile",  # Single executable file
            "--windowed",  # No console window
            f"--icon={icon_path}",
            
            # Add data files
            "--add-data=app/icon.svg;app",
            "--add-data=app/icon.png;app",
            "--add-data=assents/sounds;assents/sounds",  # Include sounds directory
            
            # Hidden imports that PyInstaller might miss
            "--hidden-import=PySide6.QtSvg",
            "--hidden-import=PySide6.QtSvgWidgets",
            "--hidden-import=app.portable_data",
            "--hidden-import=app.ghost_manager",
            "--hidden-import=app.stats_db",
            "--hidden-import=app.settings",
            
            # Clean build
            "--clean",
            
            # Entry point
            str(entry_script)
        ]
        
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, check=True, cwd=self.root)
            print("\n✅ Windows build complete!")
            print(f"   Executable: {self.dist_dir / 'dev_type.exe'}")
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Build failed with error code {e.returncode}")
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            return False
    
    def build_linux(self):
        """Build Linux executable."""
        print("🏗️  Building Linux executable...\n")
        
        icon_path = self.get_icon_path()
        
        # Create a temporary entry point script
        entry_script = self.root / "run_app.py"
        entry_script.write_text("""#!/usr/bin/env python
# Temporary entry point for PyInstaller build
if __name__ == "__main__":
    from app.ui_main import run_app
    run_app()
""")
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--name=dev_type",
            "--onefile",  # Single executable file
            f"--icon={icon_path}",
            
            # Add data files
            "--add-data=app/icon.svg:app",
            "--add-data=app/icon.png:app",
            "--add-data=assents/sounds:assents/sounds",  # Include sounds directory
            
            # Hidden imports
            "--hidden-import=PySide6.QtSvg",
            "--hidden-import=PySide6.QtSvgWidgets",
            "--hidden-import=app.portable_data",
            "--hidden-import=app.ghost_manager",
            "--hidden-import=app.stats_db",
            "--hidden-import=app.settings",
            
            # Clean build
            "--clean",
            
            # Entry point
            str(entry_script)
        ]
        
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, check=True, cwd=self.root)
            print("\n✅ Linux build complete!")
            print(f"   Executable: {self.dist_dir / 'dev_type'}")
            print("\n📦 To create AppImage:")
            print("   1. Download appimagetool from https://appimage.github.io/")
            print("   2. Create AppDir structure:")
            print("      mkdir -p AppDir/usr/bin")
            print("      cp dist/dev_type AppDir/usr/bin/")
            print("      cp app/icon.png AppDir/dev_type.png")
            print("   3. Create dev_type.desktop file in AppDir/")
            print("   4. Run: appimagetool AppDir dev_type.AppImage")
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Build failed with error code {e.returncode}")
            
            # Clean up temporary entry script
            if entry_script.exists():
                entry_script.unlink()
            
            return False
    
    def build(self, target: str = "current"):
        """Build for specified target platform."""
        if self.clean_first:
            self.clean()
        
        if not self.check_pyinstaller():
            return False
        
        success = True
        
        if target == "current":
            if self.is_windows:
                success = self.build_windows()
            elif self.is_linux:
                success = self.build_linux()
            elif self.is_mac:
                print("⚠️  macOS build not yet implemented")
                print("   Linux build process should work with minor adjustments")
                success = False
            else:
                print(f"❌ Unsupported platform: {self.system}")
                success = False
        
        elif target == "windows":
            success = self.build_windows()
        
        elif target == "linux":
            success = self.build_linux()
        
        elif target == "all":
            print("Building for all platforms...\n")
            if self.is_windows:
                success = self.build_windows()
            elif self.is_linux:
                success = self.build_linux()
            else:
                print("⚠️  Building for multiple platforms from this OS not supported")
                success = False
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build portable executables for dev_type")
    parser.add_argument("--windows", action="store_true", help="Build Windows executable")
    parser.add_argument("--linux", action="store_true", help="Build Linux executable")
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
    
    success = builder.build(target)
    
    if success:
        print("\n" + "=" * 60)
        print("  ✅ BUILD SUCCESSFUL")
        print("=" * 60)
        print("\n📋 Next steps:")
        print("   1. Test the executable in dist/")
        print("   2. The 'data' folder will be created automatically on first run")
        print("   3. To update: just replace the executable, keep the data folder")
        return 0
    else:
        print("\n" + "=" * 60)
        print("  ❌ BUILD FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
