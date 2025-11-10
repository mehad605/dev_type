"""Sound effects manager for typing feedback - keypress only."""
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl, QObject, Signal
from pathlib import Path
from typing import Dict, Optional
import json


class SoundManager(QObject):
    """Manages typing keypress sound effects."""
    
    profile_changed = Signal(str)  # Emitted when profile changes
    
    def __init__(self):
        super().__init__()
        self.current_profile = "none"
        self.sound_effect: Optional[QSoundEffect] = None
        self.enabled = True
        self.volume = 0.5
        
        # Base sounds directory
        self.sounds_dir = Path(__file__).parent.parent / "assents" / "sounds"
        
        # Custom profiles directory
        self.custom_profiles_dir = self.sounds_dir / "custom"
        self.custom_profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover built-in profiles from existing files
        self.builtin_profiles = self._discover_builtin_profiles()
        
        # Load custom profiles from disk
        self.custom_profiles = self._load_custom_profiles()
        
        self._load_profile("none")
    
    def _discover_builtin_profiles(self) -> Dict:
        """Discover built-in sound profiles from keypress_* files."""
        profiles = {
            "none": {
                "name": "No Sound",
                "builtin": True,
                "file": None
            }
        }
        
        # Scan for keypress_*.wav and keypress_*.mp3 files
        if self.sounds_dir.exists():
            for file in self.sounds_dir.glob("keypress_*"):
                if file.suffix.lower() in ['.wav', '.mp3', '.ogg']:
                    # Extract name from filename (keypress_something.wav -> something)
                    name_part = file.stem.replace("keypress_", "")
                    # Capitalize name
                    display_name = name_part.capitalize()
                    
                    profile_id = name_part.lower()
                    profiles[profile_id] = {
                        "name": display_name,
                        "builtin": True,
                        "file": file.name
                    }
        
        return profiles
    
    def _load_custom_profiles(self) -> Dict:
        """Load custom sound profiles from JSON file."""
        profiles_file = self.custom_profiles_dir / "profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading custom profiles: {e}")
        return {}
    
    def _save_custom_profiles(self):
        """Save custom profiles to JSON file."""
        profiles_file = self.custom_profiles_dir / "profiles.json"
        try:
            with open(profiles_file, 'w') as f:
                json.dump(self.custom_profiles, f, indent=2)
        except Exception as e:
            print(f"Error saving custom profiles: {e}")
    
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
        if profile_id in self.builtin_profiles:
            return False  # Can't override built-in
        
        if not Path(sound_file).exists():
            return False
        
        # Copy sound file to custom directory
        profile_dir = self.custom_profiles_dir / profile_id
        profile_dir.mkdir(exist_ok=True)
        
        dest = profile_dir / f"keypress{Path(sound_file).suffix}"
        import shutil
        shutil.copy2(sound_file, dest)
        
        # Save profile metadata
        self.custom_profiles[profile_id] = {
            "name": name,
            "builtin": False,
            "file": dest.name
        }
        
        self._save_custom_profiles()
        return True
    
    def update_custom_profile(self, profile_id: str, sound_file: str = None, name: str = None) -> bool:
        """Update a custom profile's sound file or name."""
        if profile_id not in self.custom_profiles:
            return False
        
        # Update name if provided
        if name:
            self.custom_profiles[profile_id]["name"] = name
        
        # Update sound file if provided
        if sound_file and Path(sound_file).exists():
            # Copy file to profile directory
            profile_dir = self.custom_profiles_dir / profile_id
            profile_dir.mkdir(exist_ok=True)
            
            dest = profile_dir / f"keypress{Path(sound_file).suffix}"
            import shutil
            shutil.copy2(sound_file, dest)
            
            # Update metadata
            self.custom_profiles[profile_id]["file"] = dest.name
        
        self._save_custom_profiles()
        
        # Reload if this is the current profile
        if self.current_profile == profile_id:
            self._load_profile(profile_id)
        
        return True
    
    def delete_custom_profile(self, profile_id: str) -> bool:
        """Delete a custom profile."""
        if profile_id not in self.custom_profiles:
            return False
        
        # Delete directory
        profile_dir = self.custom_profiles_dir / profile_id
        if profile_dir.exists():
            import shutil
            shutil.rmtree(profile_dir)
        
        # Remove from metadata
        del self.custom_profiles[profile_id]
        self._save_custom_profiles()
        
        # Switch to none if this was active
        if self.current_profile == profile_id:
            self.set_profile("none")
        
        return True
    
    def _load_profile(self, profile: str):
        """Load sound file for a profile."""
        # Clean up old sound
        if self.sound_effect:
            try:
                self.sound_effect.stop()
                self.sound_effect.setSource(QUrl())  # Clear source URL
            except RuntimeError:
                pass  # Already deleted
            
            # Important: Delete immediately and clear reference
            old_effect = self.sound_effect
            self.sound_effect = None
            old_effect.deleteLater()
        
        if profile == "none":
            return
        
        # Get profile data (built-in or custom)
        all_profiles = self.get_all_profiles()
        profile_data = all_profiles.get(profile)
        if not profile_data or not profile_data.get("file"):
            return
        
        # Determine file path
        if profile_data.get("builtin"):
            sound_path = self.sounds_dir / profile_data["file"]
        else:
            sound_path = self.custom_profiles_dir / profile / profile_data["file"]
        
        # Load sound file
        if sound_path.exists():
            self.sound_effect = QSoundEffect(self)  # Set parent to prevent premature deletion
            self.sound_effect.setSource(QUrl.fromLocalFile(str(sound_path)))
            self.sound_effect.setVolume(self.volume)
            
            # Debug: Print loading info
            print(f"[SoundManager] Loaded '{profile}': {sound_path}")
            print(f"[SoundManager] Volume: {self.volume}, Enabled: {self.enabled}")
        else:
            print(f"[SoundManager] ERROR: File not found: {sound_path}")
            self.sound_effect = None
    
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
                # Object already deleted
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
                print(f"[SoundManager] Error loading sound, reloading...")
                self._load_profile(self.current_profile)
            else:
                print(f"[SoundManager] Sound status: {status}")
        except RuntimeError:
            # Object already deleted
            print("[SoundManager] Sound effect was deleted")
            self.sound_effect = None
    
    def get_profile_sound_file(self, profile_id: str) -> Optional[str]:
        """Get the file path for a profile's sound."""
        all_profiles = self.get_all_profiles()
        profile_data = all_profiles.get(profile_id)
        if not profile_data or not profile_data.get("file"):
            return None
        
        if profile_data.get("builtin"):
            path = self.sounds_dir / profile_data["file"]
        else:
            path = self.custom_profiles_dir / profile_id / profile_data["file"]
        
        return str(path) if path.exists() else None


# Global instance
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get or create the global sound manager."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
