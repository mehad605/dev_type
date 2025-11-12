"""Ghost replay manager for storing and loading best typing sessions."""
import json
import gzip
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Import portable data manager for exe/AppImage builds
try:
    from app.portable_data import get_ghosts_dir
    _PORTABLE_MODE_AVAILABLE = True
except ImportError:
    _PORTABLE_MODE_AVAILABLE = False
    def get_ghosts_dir():
        return Path("ghosts")


class GhostManager:
    """Manages ghost replay data - stores only the best session per file."""
    
    def __init__(self):
        # Always use portable ghosts directory (works in both dev and exe mode)
        if _PORTABLE_MODE_AVAILABLE:
            self.ghosts_dir = get_ghosts_dir()
        else:
            self.ghosts_dir = Path("ghosts")
        
        self.ghosts_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file content to detect changes."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception as e:
            print(f"Error hashing file: {e}")
            return hashlib.sha256(file_path.encode()).hexdigest()[:16]
    
    def _get_ghost_path(self, file_path: str) -> Path:
        """Get the ghost file path for a source file."""
        file_hash = self._get_file_hash(file_path)
        return self.ghosts_dir / f"{file_hash}.json.gz"
    
    def should_save_ghost(self, file_path: str, new_wpm: float) -> bool:
        """Check if this session is better than existing ghost."""
        ghost_file = self._get_ghost_path(file_path)
        
        if not ghost_file.exists():
            return True  # First completion
        
        try:
            # Load existing ghost
            with gzip.open(ghost_file, 'rt', encoding='utf-8') as f:
                existing = json.load(f)
            
            return new_wpm > existing.get("wpm", 0)
        except Exception as e:
            print(f"Error reading existing ghost: {e}")
            return True  # Save if we can't read existing
    
    def save_ghost(self, file_path: str, wpm: float, accuracy: float, 
                   keystrokes: List[Dict], session_date: str = None, 
                   final_stats: dict = None, instant_death: Optional[bool] = None):
        """Save ghost session (only if it's the best)."""
        ghost_file = self._get_ghost_path(file_path)
        
        if session_date is None:
            session_date = datetime.now().isoformat()
        
        ghost_data = {
            "file": file_path,
            "hash": self._get_file_hash(file_path),
            "date": session_date,
            "wpm": round(wpm, 1),
            "acc": round(accuracy * 100, 1),  # Store as percentage
            "keys": keystrokes,  # Already in compact format: {t, k, c}
            "final_stats": final_stats
        }
        if instant_death is not None:
            ghost_data["instant_death_mode"] = bool(instant_death)
        
        try:
            # Compress and save
            with gzip.open(ghost_file, 'wt', encoding='utf-8') as f:
                json.dump(ghost_data, f, separators=(',', ':'))  # No whitespace
            
            print(f"[GhostManager] Saved ghost: {file_path} @ {wpm:.1f} WPM")
            return True
        except Exception as e:
            print(f"[GhostManager] Error saving ghost: {e}")
            return False
    
    def load_ghost(self, file_path: str) -> Optional[Dict]:
        """Load ghost for a file, or None if not available."""
        ghost_file = self._get_ghost_path(file_path)
        
        if not ghost_file.exists():
            return None
        
        try:
            with gzip.open(ghost_file, 'rt', encoding='utf-8') as f:
                ghost_data = json.load(f)
            
            # Verify file hasn't changed (optional - comment out if too strict)
            current_hash = self._get_file_hash(file_path)
            if current_hash != ghost_data.get("hash"):
                print(f"[GhostManager] Warning: File content changed since ghost was recorded")
                # Still return the ghost, but user should know
            
            return ghost_data
        except Exception as e:
            print(f"[GhostManager] Error loading ghost: {e}")
            return None
    
    def has_ghost(self, file_path: str) -> bool:
        """Check if a ghost exists for this file."""
        return self._get_ghost_path(file_path).exists()
    
    def delete_ghost(self, file_path: str) -> bool:
        """Delete ghost for a file."""
        ghost_file = self._get_ghost_path(file_path)
        try:
            if ghost_file.exists():
                ghost_file.unlink()
                print(f"[GhostManager] Deleted ghost: {file_path}")
                return True
        except Exception as e:
            print(f"[GhostManager] Error deleting ghost: {e}")
        return False
    
    def get_ghost_stats(self, file_path: str) -> Optional[Dict]:
        """Get just the stats without full keystroke data."""
        ghost_data = self.load_ghost(file_path)
        if ghost_data:
            return {
                "wpm": ghost_data.get("wpm"),
                "accuracy": ghost_data.get("acc"),
                "date": ghost_data.get("date"),
                "keystroke_count": len(ghost_data.get("keys", [])),
                "instant_death": ghost_data.get("instant_death_mode")
            }
        return None


# Global instance
_ghost_manager: Optional[GhostManager] = None


def get_ghost_manager() -> GhostManager:
    """Get or create the global ghost manager."""
    global _ghost_manager
    if _ghost_manager is None:
        _ghost_manager = GhostManager()
    return _ghost_manager
