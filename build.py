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
import os
import platform
import shutil
import subprocess
import sys
import re
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
    
    def get_version(self):
        """Get version from pyproject.toml."""
        version = "0.1.0"
        pyproject_path = self.root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                version = match.group(1)
        return version

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
        """Verify required asset files exist, attempt generation if possible."""
        print("Checking required assets...")
        
        assets_dir = self.root / "assets"
        svg_path = assets_dir / "icon.svg"
        
        required_files = [
            assets_dir / "icon.png",
            assets_dir / "sounds",
        ]
        
        if self.is_windows:
            required_files.append(assets_dir / "icon.ico")
        
        missing = [f for f in required_files if not f.exists()]
        
        if missing and svg_path.exists():
            print("   [INFO] Some icons are missing, attempting to generate from icon.svg...")
            try:
                # Use the current python interpreter to run the generator
                # Set QT_QPA_PLATFORM=offscreen to avoid needing a display
                env = os.environ.copy()
                env["QT_QPA_PLATFORM"] = "offscreen"
                subprocess.run([sys.executable, str(self.root / "app" / "generate_icon.py")], 
                               check=True, env=env, cwd=self.root)
                print("   [OK] Icons generated successfully")
                # Re-check missing
                missing = [f for f in required_files if not f.exists()]
            except Exception as e:
                print(f"   [WARN] Icon generation failed: {e}")
        
        for file_path in required_files:
            if not file_path.exists():
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
            
            # Versioned rename
            version = self.get_version()
            src = self.dist_dir / "dev_type.exe"
            dst = self.dist_dir / f"dev_type_v{version}.exe"
            
            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
                print(f"\n[SUCCESS] Windows build complete: {dst.name}")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Build failed with error code {e.returncode}")
            return False
    
    def build_linux(self):
        """Build Linux standalone executable."""
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
            "--onefile",
            f"--icon={icon_path}",
            
            # Add data files
            "--add-data=assets/icon.svg:assets",
            "--add-data=assets/icon.png:assets",
            "--add-data=assets/sounds:assets/sounds",
            
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
            
            "--noupx",
            "--clean",
            str(entry_script)
        ]
        
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(cmd, check=True, cwd=self.root)
            if entry_script.exists():
                entry_script.unlink()
            
            print("\n[SUCCESS] Linux build complete!")
            print(f"   Executable: {self.dist_dir / 'dev_type'}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Build failed with error code {e.returncode}")
            if entry_script.exists():
                entry_script.unlink()
            return False

    def build_deb(self):
        """Build Debian package (.deb)."""
        if not self.is_linux:
            print("[ERROR] .deb package can only be built on Linux!")
            return False

        print("Building Debian package...\n")

        # 1. Build the Linux binary first
        if not self.build_linux():
            return False

        # 2. Get version from pyproject.toml
        version = "0.1.0"
        pyproject_path = self.root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                version = match.group(1)

        # 3. Create package structure
        pkg_dir = self.build_dir / "deb_package"
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)
        
        # Paths
        bin_dir = pkg_dir / "usr" / "bin"
        apps_dir = pkg_dir / "usr" / "share" / "applications"
        icons_dir = pkg_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        debian_dir = pkg_dir / "DEBIAN"

        for d in [bin_dir, apps_dir, icons_dir, debian_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 4. Copy binary
        shutil.copy2(self.dist_dir / "dev_type", bin_dir / "dev_type")

        # 5. Copy icon
        icon_src = self.root / "assets" / "icon.png"
        if icon_src.exists():
            shutil.copy2(icon_src, icons_dir / "dev_type.png")

        # 6. Create desktop file
        desktop_content = f"""[Desktop Entry]
Name=Dev Type
Exec=dev_type
Icon=dev_type
Type=Application
Categories=Development;Education;
Comment=Master touch typing while coding
Terminal=false
"""
        (apps_dir / "dev_type.desktop").write_text(desktop_content)

        # 7. Create control file
        control_content = f"""Package: dev-type
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Mehad <mehad605@example.com>
Description: Master touch typing while coding
 Dev Type is a desktop application designed to help developers 
 improve their typing speed by practicing with real code snippets.
"""
        (debian_dir / "control").write_text(control_content)

        # 8. Set permissions (essential for debian packages)
        # Binary should be executable
        os.chmod(bin_dir / "dev_type", 0o755)
        # DEBIAN/control should be readable
        os.chmod(debian_dir / "control", 0o644)

        # 9. Build the package using dpkg-deb
        version = self.get_version()
        temp_deb = self.dist_dir / f"dev-type_{version}_amd64.deb"
        final_deb = self.dist_dir / f"dev_type_v{version}.deb"
        
        try:
            print(f"Running dpkg-deb to create {temp_deb.name}...")
            subprocess.run(["dpkg-deb", "--build", str(pkg_dir), str(temp_deb)], check=True)
            
            # Rename to consistent format
            if final_deb.exists():
                final_deb.unlink()
            temp_deb.rename(final_deb)
            
            print(f"\n[SUCCESS] Debian package built: {final_deb.name}")
            
            return True
        except FileNotFoundError:
            print("[ERROR] 'dpkg-deb' not found. Please install 'dpkg' package.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] dpkg-deb failed with error code {e.returncode}")
            return False

    def build(self, target: str = "current"):
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
                success = self.build_deb() # Default to .deb on Linux
            elif self.is_mac:
                print("[WARN] macOS build not yet implemented")
                success = False
            else:
                print(f"[ERROR] Unsupported platform: {self.system}")
                success = False
        
        elif target == "windows":
            success = self.build_windows()
        
        elif target == "linux":
            success = self.build_deb()
        
        elif target == "all":
            print("Building for all platforms...\n")
            if self.is_windows:
                success = self.build_windows()
            if self.is_linux:
                success = self.build_deb()
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build portable executables for dev_type")
    parser.add_argument("--windows", action="store_true", help="Build Windows executable")
    parser.add_argument("--linux", action="store_true", help="Build Linux .deb package")
    parser.add_argument("--all", action="store_true", help="Build for all platforms")
    parser.add_argument("--deb", action="store_true", help="Build Debian package (synonym for --linux)")
    parser.add_argument("--clean", action="store_true", help="Clean build directories first")
    
    args = parser.parse_args()
    
    # Determine target
    if args.windows:
        target = "windows"
    elif args.linux or args.deb:
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
