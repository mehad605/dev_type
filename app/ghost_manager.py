"""Ghost replay manager for storing and loading best typing sessions."""
import json
import gzip
import hashlib
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Import portable data manager for exe/AppImage builds
try:
    from app.portable_data import get_ghosts_dir
    _PORTABLE_MODE_AVAILABLE = True
except ImportError:
    _PORTABLE_MODE_AVAILABLE = False
    def get_ghosts_dir():
        return Path("ghosts")


def _compute_data_checksum(data: dict) -> str:
    """Compute checksum of ghost data for integrity verification.
    
    Excludes the checksum field itself from computation.
    """
    # Create a copy without the checksum field
    data_copy = {k: v for k, v in data.items() if k != 'checksum'}
    # Sort keys for consistent hashing
    json_str = json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(json_str.encode()).hexdigest()[:8]


class GhostManager:
    """Manages ghost replay data - stores only the best session per file."""
    
    def __init__(self):
        # Always use portable ghosts directory (works in both dev and exe mode)
        if _PORTABLE_MODE_AVAILABLE:
            self.ghosts_dir = get_ghosts_dir()
        else:
            self.ghosts_dir = Path("ghosts")
        
        self.ghosts_dir.mkdir(parents=True, exist_ok=True)
        self._last_error: Optional[str] = None
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file content to detect changes."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Error hashing file {file_path}: {e}")
            return hashlib.sha256(file_path.encode()).hexdigest()[:16]
    
    def _get_ghost_path(self, file_path: str) -> Path:
        """Get the ghost file path for a source file."""
        file_hash = self._get_file_hash(file_path)
        return self.ghosts_dir / f"{file_hash}.json.gz"
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self._last_error
    
    def clear_error(self):
        """Clear the last error message."""
        self._last_error = None
    
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
            logger.warning(f"Error reading existing ghost for comparison: {e}")
            return True  # Save if we can't read existing
    
    def save_ghost(self, file_path: str, wpm: float, accuracy: float, 
                   keystrokes: List[Dict], session_date: str = None, 
                   final_stats: dict = None, instant_death: Optional[bool] = None,
                   wpm_history: List[tuple] = None, error_history: List[tuple] = None):
        """Save ghost session (only if it's the best)."""
        ghost_file = self._get_ghost_path(file_path)
        self._last_error = None
        
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
        
        # Store WPM and error history for graph display (saves recalculation)
        if wpm_history:
            ghost_data["wpm_history"] = wpm_history
        if error_history:
            ghost_data["error_history"] = error_history
        
        # Add checksum for integrity verification
        ghost_data["checksum"] = _compute_data_checksum(ghost_data)
        
        try:
            # Atomic save: write to temp file first, then rename
            ghost_file.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(suffix='.tmp', dir=ghost_file.parent)
            try:
                with gzip.open(temp_path, 'wt', encoding='utf-8') as f:
                    json.dump(ghost_data, f, separators=(',', ':'))  # No whitespace
                os.close(fd)
                # Atomic rename (same filesystem guarantees atomicity)
                os.replace(temp_path, ghost_file)
            except Exception:
                os.close(fd) if not os.get_inheritable(fd) else None
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
            
            print(f"[GhostManager] Saved ghost: {file_path} @ {wpm:.1f} WPM")
            logger.info(f"Saved ghost: {file_path} @ {wpm:.1f} WPM")
            return True
        except Exception as e:
            error_msg = f"Failed to save ghost data: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False
    
    def load_ghost(self, file_path: str) -> Optional[Dict]:
        """Load ghost for a file, or None if not available."""
        ghost_file = self._get_ghost_path(file_path)
        self._last_error = None
        
        if not ghost_file.exists():
            return None
        
        try:
            with gzip.open(ghost_file, 'rt', encoding='utf-8') as f:
                ghost_data = json.load(f)
            
            # Verify checksum if present (backwards compatible with old ghosts)
            stored_checksum = ghost_data.get("checksum")
            if stored_checksum:
                computed_checksum = _compute_data_checksum(ghost_data)
                if stored_checksum != computed_checksum:
                    error_msg = f"Ghost data checksum mismatch: {ghost_file.name}"
                    logger.error(f"{error_msg} (stored={stored_checksum}, computed={computed_checksum})")
                    self._last_error = error_msg
                    self._attempt_recovery(ghost_file, "checksum mismatch")
                    return None
            
            # Verify file hasn't changed (optional - comment out if too strict)
            current_hash = self._get_file_hash(file_path)
            if current_hash != ghost_data.get("hash"):
                logger.warning(f"File content changed since ghost was recorded: {file_path}")
                # Still return the ghost, but user should know
            
            return ghost_data
        except gzip.BadGzipFile as e:
            error_msg = f"Ghost data corrupted (invalid gzip): {ghost_file.name}"
            logger.error(error_msg)
            self._last_error = error_msg
            self._attempt_recovery(ghost_file, "corrupted gzip")
            return None
        except json.JSONDecodeError as e:
            error_msg = f"Ghost data corrupted (invalid JSON): {ghost_file.name}"
            logger.error(f"{error_msg} - {e}")
            self._last_error = error_msg
            self._attempt_recovery(ghost_file, "invalid JSON")
            return None
        except Exception as e:
            error_msg = f"Failed to load ghost data: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
            return None
    
    def _attempt_recovery(self, ghost_file: Path, reason: str):
        """Attempt to recover from corrupted ghost file by backing it up."""
        try:
            backup_path = ghost_file.with_suffix('.corrupted')
            if ghost_file.exists():
                ghost_file.rename(backup_path)
                logger.info(f"Backed up corrupted ghost file to {backup_path}")
        except Exception as e:
            logger.warning(f"Could not backup corrupted ghost file: {e}")
            try:
                ghost_file.unlink()
                logger.info(f"Deleted corrupted ghost file: {ghost_file}")
            except Exception:
                pass
    
    def has_ghost(self, file_path: str) -> bool:
        """Check if a ghost exists for this file."""
        return self._get_ghost_path(file_path).exists()
    
    def delete_ghost(self, file_path: str) -> bool:
        """Delete ghost for a file."""
        ghost_file = self._get_ghost_path(file_path)
        self._last_error = None
        try:
            if ghost_file.exists():
                ghost_file.unlink()
                logger.info(f"Deleted ghost: {file_path}")
                return True
        except Exception as e:
            error_msg = f"Failed to delete ghost: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
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


    def refresh(self):
        """Refresh the ghosts directory, typically called after a profile switch."""
        if _PORTABLE_MODE_AVAILABLE:
            from app.portable_data import get_ghosts_dir
            self.ghosts_dir = get_ghosts_dir()
        else:
            self.ghosts_dir = Path("ghosts")
        
        self.ghosts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GhostManager refreshed. Current ghosts dir: {self.ghosts_dir}")


# Global instance
_ghost_manager: Optional[GhostManager] = None


def get_ghost_manager() -> GhostManager:
    """Get or create the global ghost manager."""
    global _ghost_manager
    if _ghost_manager is None:
        _ghost_manager = GhostManager()
    return _ghost_manager
