"""
Portable Data Directory Manager

This module handles the creation and management of a portable data directory
that sits alongside the executable/AppImage. This enables:
1. True portable distribution (no installation needed)
2. Easy updates (replace exe, keep data folder)
3. User data persistence across versions
4. Custom data directory location (configurable by user)

Directory Structure:
    dev_type.exe or dev_type.AppImage
    Dev_Type_Data/
        typing_stats.db   (SQLite database)
        ghosts/           (Ghost replay files)
        custom_sounds/    (User's custom sound profiles)
        settings/         (Future: custom settings exports)
        logs/             (Future: application logs)

The Dev_Type_Data folder is created automatically on first run if it doesn't exist.
User can change the data directory location via settings.

Configuration File Locations:
    Windows: %APPDATA%\\DevType\\config.ini
    Linux:   ~/.config/devtype/config.conf
"""
import logging
import os
import sys
import platform
import configparser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)



class PortableDataManager:
    """Manages portable data directory for the application."""
    
    _instance: Optional['PortableDataManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the portable data manager."""
        if self._initialized:
            return
            
        self._base_dir: Optional[Path] = None
        self._data_dir: Optional[Path] = None
        self._custom_data_dir: Optional[Path] = None  # User-specified location
        self._is_portable: bool = False
        self._last_error: Optional[str] = None
        self._active_profile: str = "Default"
        
        self._detect_and_setup()
        self._initialized = True
    
    def _detect_and_setup(self):
        """Detect if running as portable app and setup data directory."""
        # Determine the base directory (where the exe/AppImage is)
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (PyInstaller)
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                # The actual executable is in sys.executable
                self._base_dir = Path(sys.executable).parent
                self._is_portable = True
            else:
                self._base_dir = Path(sys.executable).parent
                self._is_portable = True
        else:
            # Running as Python script (development mode)
            # Use the project root directory
            self._base_dir = Path(__file__).parent.parent
            self._is_portable = False
        
        # Priority Logic:
        # 1. Check for User Custom Path in AppData/Config
        self._load_custom_data_dir()
        
        # 2. Determine default data directory based on platform
        local_data = self._base_dir / "Dev_Type_Data"
        
        # DECISION:
        # 1. If user explicitly set a custom path in settings, honor it.
        if self._custom_data_dir and self._custom_data_dir.exists():
             self._data_dir = self._custom_data_dir
             
        # 2. Platform-specific defaults
        elif platform.system() == "Windows":
            # Windows stays portable by default (local folder next to exe)
            self._data_dir = local_data
        else:
            # Linux/Mac: Default to user home directory to avoid read-only AppImage folder issues.
            # However, we still allow local portable mode if the folder already exists and is writable.
            if local_data.exists() and os.access(local_data, os.W_OK):
                self._data_dir = local_data
            else:
                # Use ~/.local/share/Dev_Type_App as standard Linux app data location
                self._data_dir = Path.home() / ".local" / "share" / "Dev_Type_App"
        
        # Create data directory and subdirectories if they don't exist
        self._ensure_directories()
    
    def _get_config_file_path(self) -> Path:
        """Get platform-specific config file path.
        
        Returns:
            Windows: %APPDATA%\\DevType\\config.ini
            Linux:   ~/.config/devtype/config.conf
        """
        system = platform.system()
        
        if system == "Windows":
            # Windows: Use APPDATA
            appdata = Path.home() / "AppData" / "Roaming"
            config_dir = appdata / "DevType"
            config_file = config_dir / "config.ini"
        else:
            # Linux/Unix: Use .config
            config_dir = Path.home() / ".config" / "devtype"
            config_file = config_dir / "config.conf"
        
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)
        
        return config_file
    
    def _load_custom_data_dir(self):
        """Load custom data directory path from platform-specific config file."""
        # First, check for old data_location.txt file and migrate if exists
        old_config_file = self._base_dir / "data_location.txt"
        if old_config_file.exists():
            try:
                path_str = old_config_file.read_text().strip()
                if path_str:
                    custom_path = Path(path_str)
                    if custom_path.exists() and custom_path.is_dir():
                        self._custom_data_dir = custom_path
                        # Migrate to new config format
                        self._save_custom_data_dir()
                        # Remove old file
                        old_config_file.unlink()
                        print(f"Migrated data directory config from data_location.txt to platform config")
                        return
            except Exception as e:
                print(f"Error migrating old config: {e}")
        
        # Load from platform-specific config file
        config_file = self._get_config_file_path()
        if not config_file.exists():
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            
            if config.has_section('Paths') and config.has_option('Paths', 'data_directory'):
                path_str = config.get('Paths', 'data_directory')
                if path_str:
                    custom_path = Path(path_str)
                    if custom_path.exists() and custom_path.is_dir():
                        self._custom_data_dir = custom_path
        except Exception as e:
            print(f"Error loading custom data directory from config: {e}")
    
    def _save_custom_data_dir(self):
        """Save custom data directory path to platform-specific config file."""
        config_file = self._get_config_file_path()
        
        try:
            config = configparser.ConfigParser()
            
            # Load existing config if it exists
            if config_file.exists():
                config.read(config_file)
            
            # Ensure Paths section exists
            if not config.has_section('Paths'):
                config.add_section('Paths')
            
            # Set or remove data directory
            if self._custom_data_dir:
                config.set('Paths', 'data_directory', str(self._custom_data_dir))
            else:
                # Remove the setting if no custom dir
                if config.has_option('Paths', 'data_directory'):
                    config.remove_option('Paths', 'data_directory')
            
            # Write config file
            with open(config_file, 'w') as f:
                config.write(f)
                
        except Exception as e:
            print(f"Error saving custom data directory to config: {e}")
    
    def _ensure_directories(self) -> bool:
        """Create data directory structure if it doesn't exist.
        
        Returns:
            True if directories are ready, False if permission error
        """
        self._last_error = None
        
        try:
            if not self._data_dir.exists():
                logger.info(f"Creating portable data directory: {self._data_dir}")
                self._data_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify we can write to the directory
            if not os.access(self._data_dir, os.W_OK):
                error_msg = f"No write permission for data directory: {self._data_dir}"
                logger.error(error_msg)
                self._last_error = error_msg
                self._show_permission_error(error_msg)
                return False
            
            # Create base directories for multi-profile system
            # Root structure: 
            # Dev_Type_Data/
            #   profiles/
            #   shared/
            
            profiles_dir = self._data_dir / "profiles"
            shared_dir = self._data_dir / "shared"
            
            for d in [profiles_dir, shared_dir]:
                if not d.exists():
                    d.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories in shared
            shared_subdirs = ['fonts', 'sounds', 'icons', 'logs']
            for subdir in shared_subdirs:
                subdir_path = shared_dir / subdir
                if not subdir_path.exists():
                    subdir_path.mkdir(parents=True, exist_ok=True)
            
            # Create custom sounds folder in shared
            (shared_dir / "sounds" / "custom").mkdir(parents=True, exist_ok=True)
            
            # --- ASSET COPYING LOGIC ---
            # Copy default assets (sounds) to data directory so users can customize them
            
            # 1. Determine source assets path
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller logic
                assets_src = Path(sys._MEIPASS) / "assets"
            else:
                # Dev logic
                assets_src = self._base_dir / "assets"
            
            # Copy Default Sounds
            shared_dir = self._data_dir / "shared"
            sounds_dest = shared_dir / "sounds" # Use shared sounds folder
            sounds_src = assets_src / "sounds"
            
            if not sounds_dest.exists():
                sounds_dest.mkdir(parents=True, exist_ok=True)
            
            if sounds_src.exists():
                try:
                    import shutil
                    # Copy all wav/mp3 files
                    for snd in sounds_src.glob("*.*"):
                        if snd.suffix.lower() in ['.wav', '.mp3']:
                            dest_file = sounds_dest / snd.name
                            # Efficiently copy only new/missing files
                            if not dest_file.exists():
                                shutil.copy2(snd, dest_file)
                                logger.info(f"Copied new sound to {dest_file}")
                except Exception as e:
                    logger.warning(f"Failed to copy default sounds: {e}")

            # Copy and Extract Icon Theme (if needed)
            icons_dest = self.get_icons_dir()
            # Check if icons exist (look for manifest)
            if not (icons_dest / "icons.json").exists():
                import zipfile
                import shutil
                
                icons_dest.mkdir(parents=True, exist_ok=True)
                
                # Locate zip bundle
                if hasattr(sys, '_MEIPASS'):
                     zip_src = Path(sys._MEIPASS) / "assets" / "icon-theme.zip"
                else:
                     zip_src = self._base_dir / "assets" / "icon-theme.zip"
                     
                if zip_src.exists():
                     try:
                         logger.info(f"Extracting icon theme from {zip_src} to {icons_dest}")
                         with zipfile.ZipFile(zip_src, 'r') as zf:
                             # Extract to temp then move, or extract directly depending on structure
                             # The zip we have has extension/icons
                             temp_extract = icons_dest / "_temp_extract"
                             if temp_extract.exists():
                                 shutil.rmtree(temp_extract)
                             zf.extractall(temp_extract)
                             
                             # Search for manifest to find root
                             source_icons_dir = None
                             source_manifest = None
                             
                             for root, dirs, files in os.walk(temp_extract):
                                 root_p = Path(root)
                                 if "material-icons.json" in files:
                                     source_manifest = root_p / "material-icons.json"
                                     # Look for icons dir relative to manifest or in same dir
                                     if (root_p / "icons").exists():
                                         source_icons_dir = root_p / "icons"
                                     elif (root_p / "../icons").resolve().exists():
                                         source_icons_dir = (root_p / "../icons").resolve()
                                     break
                             
                             if source_manifest and source_icons_dir:
                                 # Move files
                                 shutil.copy2(source_manifest, icons_dest / "icons.json")
                                 for svg in source_icons_dir.glob("*.svg"):
                                     shutil.copy2(svg, icons_dest / svg.name)
                                 logger.info("Icon theme extracted successfully.")
                             else:
                                 logger.warning("Could not find manifest or icons in zip bundle.")
                             
                             # Cleanup temp
                             if temp_extract.exists():
                                 shutil.rmtree(temp_extract)
                             
                     except Exception as e:
                         logger.error(f"Failed to extract icon theme: {e}")
                else:
                    logger.warning(f"Icon theme zip not found at {zip_src}")

            return True
            
        except PermissionError as e:
            error_msg = f"Permission denied creating data directory: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
            self._show_permission_error(error_msg)
            return False
        except OSError as e:
            error_msg = f"Error creating data directories: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False
    
    def _show_permission_error(self, message: str):
        """Show a user-friendly error dialog for permission issues."""
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            
            app = QApplication.instance()
            if app is None:
                print(f"ERROR: {message}")
                return
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Data Directory Error")
            msg.setText("Cannot access data directory")
            msg.setInformativeText(
                "Dev Type cannot write to its data directory. "
                "Your settings and progress may not be saved.\n\n"
                "Try running the application from a different location, "
                "or check folder permissions."
            )
            msg.setDetailedText(message)
            msg.exec()
        except Exception as e:
            logger.warning(f"Could not show permission error dialog: {e}")
            print(f"ERROR: {message}")
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self._last_error
    
    def set_data_directory(self, new_path: Path) -> bool:
        """Set a custom data directory location.
        
        Args:
            new_path: Path to the new data directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            new_path = Path(new_path)
            
            # Create if doesn't exist
            if not new_path.exists():
                new_path.mkdir(parents=True, exist_ok=True)
            
            # Validate it's a directory
            if not new_path.is_dir():
                return False
            
            # Update paths
            self._custom_data_dir = new_path
            self._data_dir = new_path
            
            # Ensure structure exists
            self._ensure_directories()
            
            # Save to config
            self._save_custom_data_dir()
            
            return True
        except Exception as e:
            print(f"Error setting data directory: {e}")
            return False
    
    def reset_to_default_directory(self) -> bool:
        """Reset data directory to default location (next to executable)."""
        try:
            self._custom_data_dir = None
            self._data_dir = self._base_dir / "Dev_Type_Data"  # Descriptive name
            self._ensure_directories()
            self._save_custom_data_dir()
            return True
        except Exception as e:
            print(f"Error resetting data directory: {e}")
            return False
    
    @property
    def is_portable(self) -> bool:
        """Check if running as portable executable."""
        return self._is_portable
    
    @property
    def base_dir(self) -> Path:
        """Get the base directory (where exe/AppImage is located)."""
        return self._base_dir
    
    def set_active_profile(self, name: str):
        """Set the active profile name to adjust dynamic paths."""
        self._active_profile = name
        # Ensure profile directory exists when set
        profile_dir = self.get_profiles_dir() / name
        if not profile_dir.exists():
            profile_dir.mkdir(parents=True, exist_ok=True)
        # Also ensure profile subdirs (like ghosts)
        (profile_dir / "ghosts").mkdir(exist_ok=True)

    @property
    def data_dir(self) -> Path:
        """Get the data directory path (root)."""
        return self._data_dir

    def get_data_dir(self) -> Path:
        """Get the data directory path."""
        return self._data_dir

    def get_profiles_dir(self) -> Path:
        """Get the directory where user profiles are stored."""
        return self.get_data_dir() / "profiles"

    def get_active_profile_dir(self) -> Path:
        """Get the directory for the currently active profile."""
        return self.get_profiles_dir() / self._active_profile

    def get_shared_dir(self) -> Path:
        """Get the directory where shared assets (fonts, sounds) are stored."""
        return self.get_data_dir() / "shared"

    def get_database_path(self) -> Path:
        """Get path to the active profile's database file."""
        return self.get_profiles_dir() / self._active_profile / "typing_stats.db"

    def get_ghosts_dir(self) -> Path:
        """Get path to the active profile's ghosts directory."""
        return self.get_profiles_dir() / self._active_profile / "ghosts"

    def get_custom_sounds_dir(self) -> Path:
        """Get path to the shared custom sounds directory."""
        return self.get_shared_dir() / "sounds" / "custom"

    def get_settings_dir(self) -> Path:
        """Get path to the active profile's settings directory (future)."""
        return self.get_profiles_dir() / self._active_profile / "settings"

    def get_logs_dir(self) -> Path:
        """Get path to the shared logs directory."""
        return self.get_shared_dir() / "logs"

    def get_fonts_dir(self) -> Path:
        """Get path to the shared fonts directory."""
        return self.get_shared_dir() / "fonts"

    def get_icons_dir(self) -> Path:
        """Get the directory where shared language icons are stored."""
        return self.get_shared_dir() / "icons"

    def get_sounds_dir(self) -> Path:
        """Get the directory where sound files are stored."""
        # Use shared sounds
        return self.get_shared_dir() / "sounds"



# Global instance
_portable_data_manager = PortableDataManager()


# Convenience functions for easy access
def get_data_manager() -> PortableDataManager:
    """Get the global PortableDataManager instance."""
    return _portable_data_manager


def get_database_path() -> Path:
    """Get path to the database file."""
    return _portable_data_manager.get_database_path()


def get_ghosts_dir() -> Path:
    """Get path to the ghosts directory."""
    return _portable_data_manager.get_ghosts_dir()


def get_custom_sounds_dir() -> Path:
    """Get path to the custom sounds directory."""
    return _portable_data_manager.get_custom_sounds_dir()


def get_fonts_dir() -> Path:
    """Get path to the fonts directory."""
    return _portable_data_manager.get_fonts_dir()


def get_icons_dir() -> Path:
    """Get path to the icons directory."""
    return _portable_data_manager.get_icons_dir()


def is_portable() -> bool:
    """Check if running as portable executable."""
    return _portable_data_manager.is_portable


def get_data_dir() -> Path:
    """Get the data directory path."""
    return _portable_data_manager.data_dir


if __name__ == "__main__":
    # Test/debug output
    manager = get_data_manager()
    info = manager.get_info()
    
    print("=== Portable Data Manager Info ===")
    for key, value in info.items():
        print(f"{key:20s}: {value}")
