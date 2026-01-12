import json
import shutil
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from PySide6.QtCore import QObject, Signal

from app.portable_data import get_data_manager

logger = logging.getLogger(__name__)

class ProfileManager(QObject):
    """
    Manages user profiles, migration, and active session state.
    
    Directory Structure:
      Dev_Type_Data/
        global_config.json
        shared/
          sounds/
          fonts/
        profiles/
          Default/
            typing_stats.db
            settings.json (future)
          User2/
            ...
    """
    
    # Signals
    profile_switched = Signal(str)  # Emitted when active profile changes
    profile_created = Signal(str)
    profile_deleted = Signal(str)
    profile_updated = Signal(str)  # Name of updated profile
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProfileManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self._data_manager = get_data_manager()
        self._profiles_dir = self._data_manager.get_profiles_dir()
        self._shared_dir = self._data_manager.get_shared_dir()
        
        # Everything shared goes in shared, including global config
        self._global_config_path = self._shared_dir / "global_config.json"
        
        self.active_profile = "Default"
        self._load_global_config() 
        self._data_manager.set_active_profile(self.active_profile)
        
        self._ensure_structure()
        self._migrate_legacy_data_if_needed()
        
        self._initialized = True

    def _ensure_structure(self):
        """Ensure base directories exist."""
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._shared_dir.mkdir(parents=True, exist_ok=True)
        (self._shared_dir / "sounds").mkdir(exist_ok=True)
        (self._shared_dir / "fonts").mkdir(exist_ok=True)
        (self._shared_dir / "icons").mkdir(exist_ok=True)

    def _migrate_legacy_data_if_needed(self):
        """
        Check for legacy data in root and move it to Default profile.
        Legacy items: typing_stats.db, ghosts/, custom_sounds/ -> (move to shared or profile?)
        """
        data_dir = self._data_manager.get_data_dir()
        
        # Check if we already have a Default profile with data
        default_profile_dir = self._profiles_dir / "Default"
        if default_profile_dir.exists() and (default_profile_dir / "typing_stats.db").exists():
            return  # Migration already likely done
            
        # Check for legacy DB
        legacy_db = data_dir / "typing_stats.db"
        if not legacy_db.exists():
            # Brand new install, just create Default profile
            self.create_profile("Default", None)
            return

        logger.info("Migrating legacy data to Default profile...")
        
        # Create Default profile folder
        default_profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Move DB
        try:
            shutil.move(str(legacy_db), str(default_profile_dir / "typing_stats.db"))
        except Exception as e:
            logger.error(f"Failed to move legacy DB: {e}")

        # Move Ghosts (Profile specific)
        legacy_ghosts = data_dir / "ghosts"
        if legacy_ghosts.exists():
            try:
                shutil.move(str(legacy_ghosts), str(default_profile_dir / "ghosts"))
            except Exception as e:
                logger.error(f"Failed to move ghosts: {e}")
                
        # Move Custom Sounds (Shared)
        legacy_sounds = data_dir / "custom_sounds"
        if legacy_sounds.exists():
            try:
                dest = self._shared_dir / "sounds" / "custom"
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(legacy_sounds), str(dest))
            except Exception as e:
                logger.error(f"Failed to move custom sounds: {e}")

        # Move Language Snapshot (to Default Profile)
        default_p_dir = self._profiles_dir / "Default"
        dest_snapshot = default_p_dir / "language_snapshot.json"
        
        # Check root and shared for legacy snapshots
        for src_snapshot in [data_dir / "language_snapshot.json", self._shared_dir / "language_snapshot.json"]:
            if src_snapshot.exists():
                try:
                    if not dest_snapshot.exists():
                        shutil.move(str(src_snapshot), str(dest_snapshot))
                        logger.info(f"Migrated language snapshot to {dest_snapshot}")
                    else:
                        src_snapshot.unlink() # Cleanup duplicates
                except Exception as e:
                    logger.error(f"Failed to move language snapshot: {e}")

        # Cleanup empty legacy folders in root
        legacy_folders = ['ghosts', 'custom_sounds', 'settings', 'logs', 'fonts', 'sounds']
        for folder_name in legacy_folders:
            folder_path = data_dir / folder_name
            if folder_path.exists() and folder_path.is_dir():
                try:
                    # Only remove if empty or we already moved what we cared about
                    if not any(folder_path.iterdir()):
                        folder_path.rmdir()
                    else:
                        # If not empty, maybe move remaining to shared or just leave for manual cleanup
                        # For safety, let's just log it
                        logger.debug(f"Legacy folder {folder_name} is not empty, skipping delete.")
                except Exception as e:
                    logger.debug(f"Failed to cleanup legacy folder {folder_name}: {e}")

        # ensure Default is active
        self.active_profile = "Default"
        self._save_global_config()

    def _load_global_config(self):
        # Look in new location first
        config_path = self._global_config_path
        
        # Migrate from old location if exists
        old_config = self._data_manager.get_data_dir() / "global_config.json"
        if old_config.exists() and not config_path.exists():
            try:
                shutil.move(str(old_config), str(config_path))
                logger.info(f"Migrated global_config.json to {config_path}")
            except Exception as e:
                logger.error(f"Failed to migrate global config: {e}")

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_profile = data.get("active_profile", "Default")
            except Exception as e:
                logger.error(f"Failed to load global config: {e}")
        else:
            self.active_profile = "Default"
            self._save_global_config()
            
    def _save_global_config(self):
        data = {
            "active_profile": self.active_profile
        }
        try:
            with open(self._global_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save global config: {e}")

    def get_active_profile(self) -> str:
        return self.active_profile

    def get_all_profiles(self) -> List[Dict]:
        """Return list of profile dicts: {name: str, image: str or None}.
        Profiles are returned in creation order (based on directory creation time).
        """
        profiles = []
        if not self._profiles_dir.exists():
            return profiles
            
        for path in self._profiles_dir.iterdir():
            if path.is_dir():
                # Check for profile.json metadata
                meta_path = path / "profile.json"
                image_path = None
                creation_time = path.stat().st_ctime  # Directory creation time
                
                if meta_path.exists():
                    try:
                        with open(meta_path, "r") as f:
                            data = json.load(f)
                            image_path = data.get("image")
                            # Use stored creation_order if available, otherwise use file system time
                            creation_time = data.get("creation_order", creation_time)
                    except:
                        pass
                
                profiles.append({
                    "name": path.name,
                    "image": image_path,
                    "is_active": (path.name == self.active_profile),
                    "creation_time": creation_time
                })
        
        # Sort by creation time to maintain insertion order (oldest first)
        # This ensures profiles stay in the order they were created
        profiles.sort(key=lambda x: x["creation_time"])
        
        # Remove creation_time from output (internal use only)
        for p in profiles:
            del p["creation_time"]
        
        return profiles

    def create_profile(self, name: str, image_path: str = None) -> bool:
        target_dir = self._profiles_dir / name
        if target_dir.exists():
            return False
            
        try:
            target_dir.mkdir(parents=True)
            
            # Save metadata with creation timestamp
            import time
            meta = {
                "image": image_path,
                "creation_order": time.time()  # Store creation time for consistent ordering
            }
            with open(target_dir / "profile.json", "w") as f:
                json.dump(meta, f)
                
            # Create empty DB (will be handled by settings.init_db when switched)
            
            self.profile_created.emit(name)
            return True
        except Exception as e:
            logger.error(f"Failed to create profile {name}: {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        all_profiles = self.get_all_profiles()
        if len(all_profiles) <= 1:
            return False # Cannot delete the only profile
            
        target_dir = self._profiles_dir / name
        if not target_dir.exists():
            return False
            
        try:
            shutil.rmtree(target_dir)
            self.profile_deleted.emit(name)
            
            if self.active_profile == name:
                self.switch_profile("Default")
                
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile {name}: {e}")
            return False

    def switch_profile(self, name: str):
        if name == self.active_profile:
            return
            
        target_dir = self._profiles_dir / name
        if not target_dir.exists():
            logger.error(f"Cannot switch to non-existent profile: {name}")
            return
            
        self.active_profile = name
        self._data_manager.set_active_profile(name)
        self._save_global_config()
        self.profile_switched.emit(name)

    def get_current_db_path(self) -> Path:
        return self._profiles_dir / self.active_profile / "typing_stats.db"

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile and its directory."""
        if old_name == new_name:
            return True
        if not new_name or new_name.strip() == "":
            return False
            
        old_dir = self._profiles_dir / old_name
        new_dir = self._profiles_dir / new_name
        
        if not old_dir.exists() or new_dir.exists():
            return False
            
        try:
            # Rename folder
            old_dir.rename(new_dir)
            
            # If active, update internal state
            if self.active_profile == old_name:
                self.active_profile = new_name
                self._data_manager.set_active_profile(new_name)
                self._save_global_config()
            
            self.profile_updated.emit(new_name)
            return True
        except Exception as e:
            logger.error(f"Failed to rename profile {old_name} to {new_name}: {e}")
            return False

    def update_profile_image(self, name: str, image_path: str):
        target_dir = self._profiles_dir / name
        if not target_dir.exists():
            return
            
        meta_path = target_dir / "profile.json"
        data = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    data = json.load(f)
            except:
                pass
        
        data["image"] = image_path
        
        with open(meta_path, "w") as f:
            json.dump(data, f)
            
        self.profile_updated.emit(name)
            
# Global Accessor
_profile_manager = None
def get_profile_manager():
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
