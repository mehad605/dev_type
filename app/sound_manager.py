"""Sound effects manager for typing feedback - keypress only."""
import logging
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl, QObject, Signal
from pathlib import Path
from typing import Dict, Optional
import json
import app.settings as settings

logger = logging.getLogger(__name__)


class SoundManager(QObject):
    """Manages typing keypress sound effects."""
    
    profile_changed = Signal(str)  # Emitted when profile changes
    
    def __init__(self):
        super().__init__()
        self.current_profile = "none"
        self.sound_effect: Optional[QSoundEffect] = None
        self.enabled = True
        self.volume = 0.5
        self._last_error: Optional[str] = None  # Track sound loading errors
        
        # Base sounds directory (Dynamic: Prefer portable data folder)
        try:
             from app.portable_data import get_data_manager
             self.sounds_dir = get_data_manager().get_sounds_dir()
        except ImportError:
             self.sounds_dir = Path(__file__).parent.parent / "assets" / "sounds"
        
        # Custom profiles are now stored in database
        
        # Discover built-in profiles from existing files
        self.builtin_profiles = self._discover_builtin_profiles()
        
        # Load custom profiles from database
        self.custom_profiles = self._load_custom_profiles()
        
        self._load_profile("none")
    
    def _discover_builtin_profiles(self) -> Dict:
        """Discover built-in sound profiles from existing files."""
        profiles = {
            "none": {
                "name": "No Sound",
                "builtin": True,
                "file": None
            }
        }
        
        # Specifically add the new default_1 profile if keystrokes.wav exists
        keystrokes_file = self.sounds_dir / "keystrokes.wav"
        if keystrokes_file.exists():
            profiles["default_1"] = {
                "name": "Default_1",
                "builtin": True,
                "file": "keystrokes.wav"
            }
        
        # Scan for all .wav files to be inclusive of new user additions
        if self.sounds_dir.exists():
            for file in self.sounds_dir.glob("*.wav"):
                # Skip the default keystrokes.wav if we already handled it
                if file.name == "keystrokes.wav":
                    continue
                    
                # Extract name
                stem = file.stem
                
                # User requested full names like keypress_1, keypress_2
                # We use the stem directly for both ID and display name
                name_part = stem
                
                # For display, we can just use the stem as requested 
                # (or we could Title Case it, but user asked for "keypress_1")
                display_name = name_part
                profile_id = name_part.lower()
                
                profiles[profile_id] = {
                    "name": display_name,
                    "builtin": True,
                    "file": file.name
                }
        
        return profiles
    
    def _load_custom_profiles(self) -> Dict:
        """Load custom sound profiles from database."""
        profiles = {}
        
        # Get custom profiles from settings database
        profile_data = settings.get_setting("custom_sound_profiles", settings.get_default("custom_sound_profiles"))
        try:
            profiles = json.loads(profile_data)
        except Exception as e:
            logger.warning(f"Error loading custom profiles from database: {e}")
        
        return profiles
    
    def _save_custom_profiles(self):
        """Save custom profiles to database."""
        try:
            profile_data = json.dumps(self.custom_profiles)
            settings.set_setting("custom_sound_profiles", profile_data)
        except Exception as e:
            logger.warning(f"Error saving custom profiles to database: {e}")
    
    def get_all_profiles(self) -> Dict:
        """Get both built-in and custom profiles."""
        all_profiles = dict(self.builtin_profiles)
        all_profiles.update(self.custom_profiles)
        return all_profiles
    
    def get_profile_names(self) -> Dict[str, str]:
        """Get profile IDs and their display names."""
        profiles = self.get_all_profiles()
        return {pid: pdata["name"] for pid, pdata in profiles.items()}
    
    def create_custom_profile(self, profile_id: str, name: str, sound_file: str) -> bool:
        """Create a new custom sound profile."""
        # Note: We now allow overriding built-in names which will take precedence
        # in get_all_profiles()
        
        if not Path(sound_file).exists() or not sound_file.lower().endswith(".wav"):
            return False
        
        # Get custom sounds directory from portable data manager
        # Get custom sounds directory from portable data manager
        try:
            from app.portable_data import get_data_manager
            # Store custom sounds in shared/sounds/custom
            custom_sounds_dir = get_data_manager().get_shared_dir() / "sounds" / "custom"
        except:
            # Fallback
            custom_sounds_dir = self.sounds_dir / "custom"
        
        custom_sounds_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy sound file to custom directory
        profile_dir = custom_sounds_dir / profile_id
        profile_dir.mkdir(exist_ok=True)
        
        dest = profile_dir / f"keypress{Path(sound_file).suffix}"
        import shutil
        shutil.copy2(sound_file, dest)
        
        # Save profile metadata with absolute path
        self.custom_profiles[profile_id] = {
            "name": name,
            "builtin": False,
            "file_path": str(dest)  # Store absolute path
        }
        
        self._save_custom_profiles()
        return True
    
    def update_custom_profile(self, profile_id: str, sound_file: str = None, name: str = None) -> bool:
        """Update a custom profile's sound file or name."""
        # If it's a built-in not yet in custom_profiles, create a custom copy
        if profile_id not in self.custom_profiles:
            if profile_id in self.builtin_profiles:
                # Get current name if not provided
                if not name:
                    name = self.builtin_profiles[profile_id]["name"]
                
                # If no sound file provided, we'd need to copy the built-in wav.
                # However, this method is usually called with at least one change.
                # For safety, if no sound_file provided, we'll try to find the built-in one.
                if not sound_file:
                    sound_file = self.get_profile_sound_file(profile_id)
                
                if not sound_file:
                    return False
                
                # Create as custom
                result = self.create_custom_profile(profile_id, name, sound_file)
                if not result:
                    return False
            else:
                return False
        
        # Update name if provided
        if name:
            self.custom_profiles[profile_id]["name"] = name
        
        # Update sound file if provided
        if sound_file and Path(sound_file).exists():
            # Get custom sounds directory
            try:
                from app.portable_data import get_data_manager
                custom_sounds_dir = get_data_manager().get_shared_dir() / "sounds" / "custom"
            except:
                custom_sounds_dir = self.sounds_dir / "custom"
            
            custom_sounds_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to profile directory
            profile_dir = custom_sounds_dir / profile_id
            profile_dir.mkdir(exist_ok=True)
            
            dest = profile_dir / f"keypress{Path(sound_file).suffix}"
            import shutil
            shutil.copy2(sound_file, dest)
            
            # Update metadata with absolute path
            self.custom_profiles[profile_id]["file_path"] = str(dest)
        
        self._save_custom_profiles()
        
        # Reload if this is the current profile
        if self.current_profile == profile_id:
            self._load_profile(profile_id)
        
        return True
    
    def delete_custom_profile(self, profile_id: str) -> bool:
        """Delete a custom profile."""
        if profile_id not in self.custom_profiles:
            return False
        
        # Delete the sound file if it exists
        file_path = self.custom_profiles[profile_id].get("file_path")
        if file_path:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
            # Try to remove parent directory if empty
            try:
                file_path.parent.rmdir()
            except:
                pass
        
        # Remove from metadata
        del self.custom_profiles[profile_id]
        self._save_custom_profiles()
        
        # Switch to none if this was active
        if self.current_profile == profile_id:
            self.set_profile("none")
        
        return True
    
    def refresh(self):
        """Refresh sound profiles and directory, typically after a profile switch."""
        try:
             from app.portable_data import get_data_manager
             self.sounds_dir = get_data_manager().get_sounds_dir()
        except ImportError:
             self.sounds_dir = Path(__file__).parent.parent / "assets" / "sounds"
             
        self.builtin_profiles = self._discover_builtin_profiles()
        self.custom_profiles = self._load_custom_profiles()
        
        # Restore current profile if it still exists, else none
        old_profile = self.current_profile
        if old_profile in self.get_all_profiles():
            self._load_profile(old_profile)
        else:
            self.set_profile("none")
        
        logger.info(f"SoundManager refreshed. Custom profiles: {len(self.custom_profiles)}")

    def _load_profile(self, profile: str):
        """Load sound file for a profile."""
        if profile == "none":
            if self.sound_effect:
                self.sound_effect.stop()
                self.sound_effect.setSource(QUrl())
            return
        
        # Get profile data (built-in or custom)
        all_profiles = self.get_all_profiles()
        profile_data = all_profiles.get(profile)
        if not profile_data:
            return
        
        # Determine file path
        sound_path = None
        if profile_data.get("builtin"):
            # Built-in profile
            if profile_data.get("file"):
                sound_path = self.sounds_dir / profile_data["file"]
        else:
            # Custom profile - use file_path if available, fallback to old structure
            if "file_path" in profile_data:
                sound_path = Path(profile_data["file_path"])
            elif "file" in profile_data:
                # Legacy support
                try:
                    from app.portable_data import get_data_manager
                    custom_sounds_dir = get_data_manager().get_shared_dir() / "sounds" / "custom"
                except:
                    custom_sounds_dir = self.sounds_dir / "custom"
                sound_path = custom_sounds_dir / profile / profile_data["file"]
        
        if not sound_path:
             return

        # Load sound file
        if sound_path.exists():
            if self.sound_effect is None:
                self.sound_effect = QSoundEffect(self)
                self.sound_effect.setVolume(self.volume)
            else:
                self.sound_effect.stop()
            
            self.sound_effect.setSource(QUrl.fromLocalFile(str(sound_path)))
            self._last_error = None  # Clear any previous error
            
            logger.debug(f"Loaded sound profile '{profile}': {sound_path}")
        else:
            error_msg = f"Sound file not found: {sound_path.name}"
            logger.warning(f"Sound profile '{profile}': {error_msg}")
            self._last_error = error_msg
            if self.sound_effect:
                self.sound_effect.setSource(QUrl())
    
    def set_profile(self, profile: str):
        """Change sound profile."""
        all_profiles = self.get_all_profiles()
        if profile in all_profiles:
            self.current_profile = profile
            self._load_profile(profile)
            self.profile_changed.emit(profile)
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        if self.sound_effect and hasattr(self.sound_effect, 'setVolume'):
            try:
                self.sound_effect.setVolume(self.volume)
            except RuntimeError:
                # Object already deleted by Qt
                logger.debug("Sound effect deleted during volume change")
                self.sound_effect = None
    
    def set_enabled(self, enabled: bool):
        """Enable/disable sounds."""
        self.enabled = enabled
    
    def play_keypress(self):
        """Play keypress sound."""
        if not self.enabled:
            return
        
        if not self.sound_effect or not hasattr(self.sound_effect, 'status'):
            return
        
        try:
            # Check sound status
            status = self.sound_effect.status()
            if status == QSoundEffect.Ready:
                self.sound_effect.play()
            elif status == QSoundEffect.Error:
                error_msg = "Sound file failed to load (corrupted or unsupported format)"
                logger.warning(f"Sound profile '{self.current_profile}': {error_msg}")
                self._last_error = error_msg
                self._load_profile(self.current_profile)
            else:
                logger.debug(f"Sound status: {status}")
        except RuntimeError:
            # Object already deleted by Qt
            logger.debug("Sound effect deleted during playback")
            self.sound_effect = None
    
    def get_profile_sound_file(self, profile_id: str) -> Optional[str]:
        """Get the file path for a profile's sound."""
        all_profiles = self.get_all_profiles()
        profile_data = all_profiles.get(profile_id)
        if not profile_data or not profile_data.get("file"):
            return None
        
        if profile_data.get("builtin"):
            path = self.sounds_dir / profile_data["file"]
        elif "file_path" in profile_data:
            path = Path(profile_data["file_path"])
        else:
             # Fallback
            try:
                from app.portable_data import get_data_manager
                custom_sounds_dir = get_data_manager().get_shared_dir() / "sounds" / "custom"
            except:
                custom_sounds_dir = self.sounds_dir / "custom"
            path = custom_sounds_dir / profile_id / profile_data["file"]
        
        return str(path) if path.exists() else None
    
    def get_last_error(self) -> Optional[str]:
        """Get the last sound loading error message.
        
        Returns:
            Error message if there was a problem loading the current profile, None otherwise
        """
        return self._last_error
    
    def clear_error(self):
        """Clear the last error message."""
        self._last_error = None


# Global instance
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get or create the global sound manager."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
