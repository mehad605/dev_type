"""Icon manager for downloading and caching language icons.

This module handles downloading language icons from the devicon.dev CDN,
caching them locally, and providing fallback emoji for languages without icons.
"""
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QSize
from app.settings import get_data_dir


# Mapping of language names to devicon icon names
DEVICON_MAP = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Java": "java",
    "C": "c",
    "C++": "cplusplus",
    "C/C++ Header": "c",
    "C++ Header": "cplusplus",
    "C#": "csharp",
    "Go": "go",
    "Rust": "rust",
    "Ruby": "ruby",
    "PHP": "php",
    "Swift": "swift",
    "Kotlin": "kotlin",
    "Objective-C": "objectivec",
    "Scala": "scala",
    "R": "r",
    "Dart": "dart",
    "Lua": "lua",
    "Perl": "perl",
    "Shell": "bash",
    "Bash": "bash",
    "Zsh": "bash",
    "Fish": "bash",
    "PowerShell": "powershell",
    "SQL": "mysql",  # Generic SQL icon
    "HTML": "html5",
    "CSS": "css3",
    "SCSS": "sass",
    "Sass": "sass",
    "Less": "less",
    "XML": "xml",
    "JSON": "json",
    "YAML": "yaml",
    "TOML": "toml",
    "Markdown": "markdown",
    "Text": "txt",
}


# Emoji fallbacks for languages
EMOJI_FALLBACK = {
    "Python": "🐍",
    "JavaScript": "📜",
    "TypeScript": "📘",
    "Java": "☕",
    "C": "🔷",
    "C++": "🔷",
    "C/C++ Header": "📄",
    "C++ Header": "📄",
    "C#": "🎯",
    "Go": "🐹",
    "Rust": "🦀",
    "Ruby": "💎",
    "PHP": "🐘",
    "Swift": "🕊️",
    "Kotlin": "🅺",
    "Objective-C": "🍎",
    "Scala": "⚡",
    "R": "📊",
    "Dart": "🎯",
    "Lua": "🌙",
    "Perl": "🐪",
    "Shell": "🐚",
    "Bash": "🐚",
    "Zsh": "🐚",
    "Fish": "🐠",
    "PowerShell": "⚡",
    "SQL": "🗄️",
    "HTML": "🌐",
    "CSS": "🎨",
    "SCSS": "🎨",
    "Sass": "🎨",
    "Less": "🎨",
    "XML": "📰",
    "JSON": "📋",
    "YAML": "📋",
    "TOML": "📋",
    "Markdown": "📝",
    "Text": "📄",
}


class IconManager:
    """Manages downloading and caching of language icons."""
    
    def __init__(self):
        self.icon_dir = get_data_dir() / "icons"
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self._icon_cache: Dict[str, Optional[QPixmap]] = {}
    
    def get_icon_path(self, language: str) -> Optional[Path]:
        """Get the local path for a language icon.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
            
        Returns:
            Path to icon file if it exists, None otherwise
        """
        if language not in DEVICON_MAP:
            return None
        
        icon_name = DEVICON_MAP[language]
        icon_path = self.icon_dir / f"{icon_name}.svg"
        
        if icon_path.exists():
            return icon_path
        
        return None
    
    def download_icon(self, language: str) -> bool:
        """Download icon for a language from devicon CDN.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
            
        Returns:
            True if download succeeded, False otherwise
        """
        if language not in DEVICON_MAP:
            return False
        
        icon_name = DEVICON_MAP[language]
        icon_path = self.icon_dir / f"{icon_name}.svg"
        
        # Don't re-download if exists
        if icon_path.exists():
            return True
        
        # Devicon CDN URL - using plain colored version
        url = f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{icon_name}/{icon_name}-original.svg"
        
        try:
            # Set timeout and user agent
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Dev Typing App)'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    icon_path.write_bytes(response.read())
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            # Try alternative URL (plain version)
            try:
                url = f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{icon_name}/{icon_name}-plain.svg"
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Dev Typing App)'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        icon_path.write_bytes(response.read())
                        return True
            except Exception:
                pass  # Fail silently, will use fallback
        
        return False
    
    def get_icon(self, language: str, size: int = 48) -> Optional[QPixmap]:
        """Get icon pixmap for a language, downloading if necessary.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
            size: Desired icon size in pixels
            
        Returns:
            QPixmap with icon, or None if unavailable
        """
        # Check cache
        cache_key = f"{language}_{size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        # Try to get/download icon
        icon_path = self.get_icon_path(language)
        
        if not icon_path:
            # Try to download
            if self.download_icon(language):
                icon_path = self.get_icon_path(language)
        
        # Load icon if available
        if icon_path and icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                # Scale to desired size
                from PySide6.QtCore import Qt
                pixmap = pixmap.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._icon_cache[cache_key] = pixmap
                return pixmap
        
        # No icon available
        self._icon_cache[cache_key] = None
        return None
    
    def get_emoji_fallback(self, language: str) -> str:
        """Get emoji fallback for a language.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
            
        Returns:
            Emoji string representing the language
        """
        return EMOJI_FALLBACK.get(language, "📄")
    
    def preload_icons(self, languages: list[str]) -> None:
        """Preload icons for multiple languages in background.
        
        This can be called to download icons for all detected languages
        without blocking the UI.
        
        Args:
            languages: List of language names to preload
        """
        for language in languages:
            if language in DEVICON_MAP:
                self.download_icon(language)
    
    def clear_cache(self) -> None:
        """Clear the in-memory icon cache."""
        self._icon_cache.clear()
    
    def delete_all_icons(self) -> int:
        """Delete all downloaded icons from disk.
        
        Returns:
            Number of icons deleted
        """
        count = 0
        if self.icon_dir.exists():
            for icon_file in self.icon_dir.glob("*.svg"):
                try:
                    icon_file.unlink()
                    count += 1
                except Exception:
                    pass
        self.clear_cache()
        return count


# Global icon manager instance
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """Get the global IconManager instance.
    
    Returns:
        Global IconManager singleton
    """
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager
