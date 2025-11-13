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
import sys
import platform
import configparser
from pathlib import Path
from typing import Optional


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
        
        # Try to load custom data directory from config file
        self._load_custom_data_dir()
        
        # Data directory is the custom one if set, otherwise default
        if self._custom_data_dir and self._custom_data_dir.exists():
            self._data_dir = self._custom_data_dir
        else:
            self._data_dir = self._base_dir / "Dev_Type_Data"  # Descriptive name
        
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
    
    def _ensure_directories(self):
        """Create data directory structure if it doesn't exist."""
        if not self._data_dir.exists():
            print(f"Creating portable data directory: {self._data_dir}")
            self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['ghosts', 'custom_sounds', 'settings', 'logs']
        for subdir in subdirs:
            subdir_path = self._data_dir / subdir
            if not subdir_path.exists():
                subdir_path.mkdir(parents=True, exist_ok=True)
    
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
    
    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        return self._data_dir
    
    def get_database_path(self) -> Path:
        """Get path to the SQLite database file."""
        return self._data_dir / "typing_stats.db"
    
    def get_ghosts_dir(self) -> Path:
        """Get path to the ghosts directory."""
        return self._data_dir / "ghosts"
    
    def get_custom_sounds_dir(self) -> Path:
        """Get path to the custom sounds directory."""
        return self._data_dir / "custom_sounds"
    
    def get_settings_dir(self) -> Path:
        """Get path to the settings directory."""
        return self._data_dir / "settings"
    
    def get_logs_dir(self) -> Path:
        """Get path to the logs directory."""
        return self._data_dir / "logs"
    
    def get_info(self) -> dict:
        """Get information about the portable setup."""
        return {
            'is_portable': self._is_portable,
            'base_dir': str(self._base_dir),
            'data_dir': str(self._data_dir),
            'is_custom_location': self._custom_data_dir is not None,
            'default_data_dir': str(self._base_dir / "Dev_Type_Data"),
            'database_path': str(self.get_database_path()),
            'ghosts_dir': str(self.get_ghosts_dir()),
            'custom_sounds_dir': str(self.get_custom_sounds_dir()),
            'data_dir_exists': self._data_dir.exists(),
            'database_exists': self.get_database_path().exists(),
        }


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
