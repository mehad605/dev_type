"""
Build script for creating portable executables.

This script creates:
- Windows: dev_type.exe (single-file executable)
- Linux: dev_type (executable that can be packaged into AppImage)
- Linux: .deb and AppImage packages

Usage:
    python build.py              # Build for current platform
    python build.py --windows    # Build Windows exe
    python build.py --linux      # Build Linux .deb package
    python build.py --appimage   # Build Linux AppImage package
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
import tarfile
from datetime import datetime
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
        version = "1.0.1"
        pyproject_path = self.root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                version = match.group(1)
        return version

    def _fix_python_executable_stack(self, search_dir: Path):
        """Fix executable stack issue in all shared libraries for AppImage compatibility.

        Uses execstack to clear the executable stack flag from the main binary and
        every bundled .so file inside the PyInstaller onedir output.  This is required
        on systems / kernels that enforce a strict no-executable-stack (NX) policy,
        where libpython and other shared libs compiled with an executable stack marker
        will be refused by the dynamic linker.

        This fixes the '[PYI-xxxxx] Failed to load Python shared library' error.
        See: https://github.com/pyinstaller/pyinstaller/issues/5370

        Args:
            search_dir: Directory to recursively scan for ELF binaries/libraries.
                        For onedir builds this is the _internal/ folder next to the
                        main executable.
        """
        try:
            # Check if execstack is available
            result = subprocess.run(
                ["which", "execstack"], capture_output=True, text=True
            )

            if result.returncode != 0:
                print("   [WARN] execstack not found, cannot fix executable stack")
                print("   [HINT] Install with: sudo apt-get install execstack")
                print("   [HINT] Or: sudo dnf install execstack")
                return False

            # Collect all ELF files: the main binary and every .so under search_dir
            targets: list[Path] = []
            if search_dir.is_file():
                targets.append(search_dir)
            else:
                # The directory itself may contain the main binary as well as _internal/
                for f in search_dir.rglob("*"):
                    if f.is_file() and not f.is_symlink():
                        targets.append(f)

            if not targets:
                print(f"   [WARN] No files found in {search_dir}")
                return False

            print(f"   [INFO] Clearing executable stack flag from {len(targets)} file(s)...")
            failed = 0
            for target in targets:
                try:
                    res = subprocess.run(
                        ["execstack", "-c", str(target)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if res.returncode != 0 and res.stderr:
                        # execstack prints errors for non-ELF files; suppress those
                        if "not an ELF" not in res.stderr and "No such file" not in res.stderr:
                            print(f"   [WARN] execstack {target.name}: {res.stderr.strip()}")
                            failed += 1
                except subprocess.TimeoutExpired:
                    print(f"   [WARN] execstack timed out on {target.name}")
                    failed += 1
                except Exception as exc:
                    print(f"   [WARN] execstack failed on {target.name}: {exc}")
                    failed += 1

            if failed == 0:
                print("   [OK] Executable stack flag cleared from all bundled libraries")
                return True
            else:
                print(f"   [WARN] execstack had issues with {failed} file(s)")
                return False

        except Exception as e:
            print(f"   [WARN] Could not fix executable stack: {e}")
            return False

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
            print(
                "   [INFO] Some icons are missing, attempting to generate from icon.svg..."
            )
            try:
                # Use the current python interpreter to run the generator
                # Set QT_QPA_PLATFORM=offscreen to avoid needing a display
                env = os.environ.copy()
                env["QT_QPA_PLATFORM"] = "offscreen"
                subprocess.run(
                    [sys.executable, str(self.root / "app" / "generate_icon.py")],
                    check=True,
                    env=env,
                    cwd=self.root,
                )
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
        cmd.extend(
            [
                # Add data files
                "--add-data=assets/icon.svg;assets",
                "--add-data=assets/icon.png;assets",
                "--add-data=assets/icon.ico;assets",
                "--add-data=assets/sounds;assets/sounds",  # Include sounds directory
                "--add-data=assets/icon-theme.zip;assets",  # Bundle icon theme zip
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
                # Include Pillow for splash screen icon
                "--hidden-import=PIL",
                "--hidden-import=PIL.Image",
                "--hidden-import=PIL.ImageTk",
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
            ]
        )

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
            "--add-data=assets/icon-theme.zip:assets",
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
            str(entry_script),
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
        version = "1.0.1"
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

        # 6. Install desktop file
        desktop_src = self.root / "packaging" / "dev_type.desktop"
        if desktop_src.exists():
            shutil.copy2(desktop_src, apps_dir / "dev_type.desktop")
        else:
            print("[WARN] Missing packaging/dev_type.desktop")

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
            subprocess.run(
                ["dpkg-deb", "--build", str(pkg_dir), str(temp_deb)], check=True
            )

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

    def build_rpm(self):
        """Build RPM package (.rpm)."""
        if not self.is_linux:
            print("[ERROR] .rpm package can only be built on Linux!")
            return False

        print("Building RPM package...\n")

        # 1. Build the Linux binary first
        if not self.build_linux():
            return False

        version = self.get_version()

        # 2. Create staging root
        rpm_root = self.build_dir / "rpm_root"
        if rpm_root.exists():
            shutil.rmtree(rpm_root)

        bin_dir = rpm_root / "usr" / "bin"
        apps_dir = rpm_root / "usr" / "share" / "applications"
        icons_dir = (
            rpm_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        )
        metainfo_dir = rpm_root / "usr" / "share" / "metainfo"
        license_dir = rpm_root / "usr" / "share" / "licenses" / "dev_type"

        for d in [bin_dir, apps_dir, icons_dir, metainfo_dir, license_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 3. Copy binary
        shutil.copy2(self.dist_dir / "dev_type", bin_dir / "dev_type")
        os.chmod(bin_dir / "dev_type", 0o755)

        # 4. Copy icon
        icon_src = self.root / "assets" / "icon.png"
        if icon_src.exists():
            shutil.copy2(icon_src, icons_dir / "dev_type.png")

        # 5. Desktop file
        desktop_src = self.root / "packaging" / "dev_type.desktop"
        if desktop_src.exists():
            shutil.copy2(desktop_src, apps_dir / "dev_type.desktop")
        else:
            print("[WARN] Missing packaging/dev_type.desktop")

        # 6. AppStream metadata
        metainfo_src = (
            self.root / "packaging" / "com.github.mehad605.dev_type.metainfo.xml"
        )
        if metainfo_src.exists():
            shutil.copy2(
                metainfo_src,
                metainfo_dir / "com.github.mehad605.dev_type.metainfo.xml",
            )
        else:
            print("[WARN] Missing packaging/com.github.mehad605.dev_type.metainfo.xml")

        # 7. License
        license_src = self.root / "LICENSE"
        if license_src.exists():
            shutil.copy2(license_src, license_dir / "LICENSE")

        # 8. Build rpm tree
        rpm_build = self.build_dir / "rpm_build"
        for sub in ["BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
            (rpm_build / sub).mkdir(parents=True, exist_ok=True)

        # 9. Create source tarball
        source_dir_name = f"dev_type-{version}"
        source_tar = rpm_build / "SOURCES" / f"{source_dir_name}.tar.gz"
        if source_tar.exists():
            source_tar.unlink()

        with tarfile.open(source_tar, "w:gz") as tar:
            tar.add(rpm_root, arcname=source_dir_name)

        # 10. Spec file
        spec_path = rpm_build / "SPECS" / "dev_type.spec"
        changelog_date = datetime.now().strftime("* %a %b %d %Y")
        spec_content = f"""%define debug_package %{{nil}}
Name:           dev-type
Version:        {version}
Release:        1%{{?dist}}
Summary:        Master touch typing while coding
License:        CC-BY-NC-SA-4.0
URL:            https://github.com/mehad605/dev_type
Source0:        {source_dir_name}.tar.gz
BuildArch:      x86_64

%description
Dev Type is a desktop application designed to help developers improve their
typing speed by practicing with real code snippets.

%prep
%setup -q -n {source_dir_name}

%build

%install
mkdir -p %{{buildroot}}%{{_bindir}}
mkdir -p %{{buildroot}}%{{_datadir}}/applications
mkdir -p %{{buildroot}}%{{_datadir}}/icons/hicolor/256x256/apps
mkdir -p %{{buildroot}}%{{_datadir}}/metainfo
mkdir -p %{{buildroot}}%{{_licensedir}}/dev_type

cp -a usr/bin/dev_type %{{buildroot}}%{{_bindir}}/dev_type
cp -a usr/share/applications/dev_type.desktop %{{buildroot}}%{{_datadir}}/applications/dev_type.desktop
cp -a usr/share/icons/hicolor/256x256/apps/dev_type.png %{{buildroot}}%{{_datadir}}/icons/hicolor/256x256/apps/dev_type.png
cp -a usr/share/metainfo/com.github.mehad605.dev_type.metainfo.xml %{{buildroot}}%{{_datadir}}/metainfo/com.github.mehad605.dev_type.metainfo.xml
cp -a usr/share/licenses/dev_type/LICENSE %{{buildroot}}%{{_licensedir}}/dev_type/LICENSE

%files
%license %{{_licensedir}}/dev_type/LICENSE
%{{_bindir}}/dev_type
%{{_datadir}}/applications/dev_type.desktop
%{{_datadir}}/icons/hicolor/256x256/apps/dev_type.png
%{{_datadir}}/metainfo/com.github.mehad605.dev_type.metainfo.xml

%changelog
- {changelog_date} Mehad <mehad605@example.com> - {version}-1
- Automated build
"""
        spec_path.write_text(spec_content, encoding="utf-8")

        # 11. Build rpm
        try:
            subprocess.run(
                [
                    "rpmbuild",
                    "-bb",
                    str(spec_path),
                    "--define",
                    f"_topdir {rpm_build}",
                ],
                check=True,
                cwd=self.root,
            )

            rpm_candidates = list((rpm_build / "RPMS").rglob("*.rpm"))
            if not rpm_candidates:
                print("[ERROR] RPM build produced no artifacts.")
                return False

            rpm_output = rpm_candidates[0]
            final_rpm = self.dist_dir / f"dev_type_v{version}.rpm"
            if final_rpm.exists():
                final_rpm.unlink()
            shutil.move(str(rpm_output), str(final_rpm))

            print(f"\n[SUCCESS] RPM package built: {final_rpm.name}")
            return True
        except FileNotFoundError:
            print("[ERROR] 'rpmbuild' not found. Please install rpm-build.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] rpmbuild failed with error code {e.returncode}")
            return False

    def _build_linux_onedir(self) -> bool:
        """Build Linux onedir executable (used by AppImage build).

        Unlike build_linux() which creates a single-file executable, this produces
        a directory (dist/dev_type/) containing the main binary plus an _internal/
        folder with all bundled shared libraries.  This layout is required so that
        execstack can patch the .so files before they are packed into the AppImage.
        """
        print("Building Linux onedir executable for AppImage...\n")

        icon_path = self.get_icon_path()

        # Create a temporary entry point script
        entry_script = self.root / "run_app.py"
        entry_script.write_text("""#!/usr/bin/env python
if __name__ == "__main__":
    from app.ui_main import run_app
    run_app()
""")

        # onedir (no --onefile) so that .so files are accessible on disk
        cmd = [
            "pyinstaller",
            "--name=dev_type",
            # NOTE: --onedir is the default - explicitly stated for clarity
            "--onedir",
            f"--icon={icon_path}",
            # Data files
            "--add-data=assets/icon.svg:assets",
            "--add-data=assets/icon.png:assets",
            "--add-data=assets/sounds:assets/sounds",
            "--add-data=assets/icon-theme.zip:assets",
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
            str(entry_script),
        ]

        print(f"Command: {' '.join(cmd)}\n")

        try:
            subprocess.run(cmd, check=True, cwd=self.root)
            if entry_script.exists():
                entry_script.unlink()
            print("\n[SUCCESS] Linux onedir build complete!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Build failed with error code {e.returncode}")
            if entry_script.exists():
                entry_script.unlink()
            return False

    def build_appimage(self):
        """Build AppImage package."""
        if not self.is_linux:
            print("[ERROR] AppImage can only be built on Linux!")
            return False

        print("Building AppImage...\n")

        # 1. Build the Linux onedir binary (needed so .so files can be patched)
        if not self._build_linux_onedir():
            return False

        version = self.get_version()

        # onedir output layout: dist/dev_type/dev_type  +  dist/dev_type/_internal/
        onedir_root = self.dist_dir / "dev_type"
        onedir_bin = onedir_root / "dev_type"
        onedir_internal = onedir_root / "_internal"

        # 2. Fix executable stack on ALL bundled .so files before packaging.
        #    With --onefile the .so files are embedded inside the binary and cannot
        #    be patched.  With --onedir they live in _internal/ as real files.
        print("Patching executable stack flags on bundled libraries...")
        # Patch both the main binary and everything inside _internal/
        self._fix_python_executable_stack(onedir_root)

        # 3. Create AppDir structure
        appdir = self.build_dir / "AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)

        bin_dir = appdir / "usr" / "bin"
        apps_dir = appdir / "usr" / "share" / "applications"
        icons_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        for directory in [bin_dir, apps_dir, icons_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # 4. Copy the onedir bundle into AppDir/usr/bin/
        #    The main exe goes to usr/bin/dev_type and _internal/ goes alongside it.
        shutil.copy2(onedir_bin, bin_dir / "dev_type")
        os.chmod(bin_dir / "dev_type", 0o755)

        internal_dest = bin_dir / "_internal"
        if onedir_internal.exists():
            shutil.copytree(onedir_internal, internal_dest)
        else:
            # Older PyInstaller versions may not use _internal/; copy the whole dir
            for item in onedir_root.iterdir():
                if item.name == "dev_type":
                    continue  # already copied the main binary
                dest = bin_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        icon_src = self.root / "assets" / "icon.png"
        if icon_src.exists():
            shutil.copy2(icon_src, icons_dir / "dev_type.png")
            # AppImage also needs icon at AppDir root
            shutil.copy2(icon_src, appdir / "dev_type.png")

        # 5. Install desktop file
        desktop_src = self.root / "packaging" / "dev_type.desktop"
        if desktop_src.exists():
            shutil.copy2(desktop_src, apps_dir / "dev_type.desktop")
            shutil.copy2(desktop_src, appdir / "dev_type.desktop")
        else:
            print("[WARN] Missing packaging/dev_type.desktop")

        # 5. Install AppStream metadata
        metainfo_dir = appdir / "usr" / "share" / "metainfo"
        appdata_dir = appdir / "usr" / "share" / "appdata"
        metainfo_dir.mkdir(parents=True, exist_ok=True)
        appdata_dir.mkdir(parents=True, exist_ok=True)
        metainfo_src = (
            self.root / "packaging" / "com.github.mehad605.dev_type.metainfo.xml"
        )
        if metainfo_src.exists():
            shutil.copy2(
                metainfo_src, metainfo_dir / "com.github.mehad605.dev_type.metainfo.xml"
            )
            shutil.copy2(
                metainfo_src, appdata_dir / "com.github.mehad605.dev_type.appdata.xml"
            )
        else:
            print("[WARN] Missing packaging/com.github.mehad605.dev_type.metainfo.xml")

        # 6. Create AppRun symlink (entry point)
        apprun = appdir / "AppRun"
        if apprun.exists() or apprun.is_symlink():
            apprun.unlink()
        apprun.symlink_to("usr/bin/dev_type")
        os.chmod(apprun, 0o755)

        # 7. Download appimagetool if not present
        appimagetool = self.build_dir / "appimagetool"
        if not appimagetool.exists():
            print("Downloading appimagetool...")
            url = (
                "https://github.com/AppImage/AppImageKit/releases/download/"
                "continuous/appimagetool-x86_64.AppImage"
            )
            subprocess.run(["wget", "-q", "-O", str(appimagetool), url], check=True)
            os.chmod(appimagetool, 0o755)

        # 8. Build AppImage
        output_appimage = self.dist_dir / f"dev_type-{version}-x86_64.AppImage"
        env = os.environ.copy()
        env["ARCH"] = "x86_64"

        try:
            subprocess.run(
                [str(appimagetool), str(appdir), str(output_appimage)],
                check=True,
                env=env,
                cwd=self.root,
            )
            print(f"\n[SUCCESS] AppImage built: {output_appimage.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] appimagetool failed with error code {e.returncode}")
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
                success = self.build_deb()  # Default to .deb on Linux
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

        elif target == "rpm":
            success = self.build_rpm()

        elif target == "appimage":
            success = self.build_appimage()

        elif target == "all":
            print("Building for all platforms...\n")
            if self.is_windows:
                success = self.build_windows()
            if self.is_linux:
                deb_success = self.build_deb()
                appimage_success = self.build_appimage()
                rpm_success = self.build_rpm()
                success = deb_success and appimage_success and rpm_success

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build portable executables for dev_type"
    )
    parser.add_argument(
        "--windows", action="store_true", help="Build Windows executable"
    )
    parser.add_argument("--linux", action="store_true", help="Build Linux .deb package")
    parser.add_argument(
        "--appimage", action="store_true", help="Build Linux AppImage package"
    )
    parser.add_argument("--rpm", action="store_true", help="Build RPM package")
    parser.add_argument("--all", action="store_true", help="Build for all platforms")
    parser.add_argument(
        "--deb", action="store_true", help="Build Debian package (synonym for --linux)"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean build directories first"
    )

    args = parser.parse_args()

    # Determine target
    if args.windows:
        target = "windows"
    elif args.appimage:
        target = "appimage"
    elif args.linux or args.deb:
        target = "linux"
    elif args.rpm:
        target = "rpm"
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
