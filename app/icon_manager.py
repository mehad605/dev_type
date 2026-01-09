"""Icon manager for downloading and caching language icons.

This module handles downloading language icons from the devicon.dev CDN,
caching them locally, and providing fallback emoji for languages without icons.
"""
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QSize, QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from app.settings import get_data_dir

logger = logging.getLogger(__name__)


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
    "Markdown": "markdown",
    # Text and TOML don't have standard devicons, wil use emoji fallback

}

# Languages known to have no devicon (prevent useless 404 requests)
SKIP_ICONS = {
    "Text", "TOML", "Brainfuck", "Bf", 
    "Yaml", "Json", "Xml", # Sometimes capitalization varies, though we have specific mappings for some
}

# Dynamic lookup helper
def get_devicon_name(language: str) -> Optional[str]:
    """Get the devicon library name for a language."""
    if language in SKIP_ICONS:
        return None
        
    # 1. Check strict map
    if language in DEVICON_MAP:
        return DEVICON_MAP[language]
    
    # 2. Heuristic: try lowercase name (e.g. Brainfuck -> brainfuck)
    # Most devicons match the language name in lowercase
    return language.lower()



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


class IconManager(QObject):
    """Manages downloading and caching of language icons."""
    
    icon_downloaded = Signal(str)  # Emits language name when icon is ready

    
    def __init__(self):
        super().__init__()
        self.icon_dir = get_data_dir() / "icons"
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self._icon_cache: Dict[str, Optional[QPixmap]] = {}
        self._download_errors: Dict[str, str] = {}  # Track download failures for tooltips
        self._network_manager = QNetworkAccessManager(self)
        self._pending_downloads: Dict[QNetworkReply, str] = {} # Map reply -> language

    
    def get_icon_path(self, language: str) -> Optional[Path]:
        """Get the local path for a language icon.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
            
        Returns:
            Path to icon file if it exists, None otherwise
        """
        icon_name = get_devicon_name(language)
        if not icon_name:
             return None

        icon_path = self.icon_dir / f"{icon_name}.svg"
        
        if icon_path.exists():
            return icon_path
        
        return None

    
    def download_icon(self, language: str) -> None:
        """Initiate async download icon for a language from devicon CDN.
        
        Args:
            language: Language name (e.g., "Python", "JavaScript")
        """
        icon_name = get_devicon_name(language)
        if not icon_name:
            return

        # Check if already downloading this language? (Optional optimization)
        
        icon_path = self.icon_dir / f"{icon_name}.svg"
        
        # Don't re-download if exists
        if icon_path.exists():
            return
        
        # Devicon CDN URL - using plain colored version
        url = QUrl(f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{icon_name}/{icon_name}-original.svg")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, 'Mozilla/5.0 (Dev Typing App)')
        
        reply = self._network_manager.get(request)
        self._pending_downloads[reply] = language
        reply.finished.connect(lambda: self._on_download_finished(reply))

    def _on_download_finished(self, reply: QNetworkReply):
        language = self._pending_downloads.pop(reply, None)
        if not language:
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NoError:
            # 404s (ContentNotFoundError) are expected for unknown languages/heuristics
            # We treat them as "no icon available" and fallback to emoji silently.
            error_code = reply.error()
            error_msg = f"Network error ({error_code}): {reply.errorString()}"
            
            # Log as debug/info essentially ignoring it unless debugging
            logger.debug(f"Could not download icon for {language}: {error_msg}")
            
            # Reset error tracking so we don't show a tooltip error for just a missing icon
            # unless it's a critical network failure (e.g. no internet)?
            # Actually, simply NOT setting _download_errors[language] means no tooltip.
            # If we want to show "Offline" vs "Not Found", we'd distinguish.
            # For now, let's clearer: if it's 404, forget it. If it's connection ref, maybe show.
            if error_code == QNetworkReply.ContentNotFoundError:
                self._download_errors.pop(language, None)
            else:
                 # Real network error (timeout, dns, etc) - maybe worth noting
                 self._download_errors[language] = error_msg
        else:
            data = reply.readAll()
            if data:
                icon_name = get_devicon_name(language)
                icon_path = self.icon_dir / f"{icon_name}.svg"
                try:
                    icon_path.write_bytes(data.data())
                    logger.info(f"Downloaded icon for {language}")
                    self._download_errors.pop(language, None)
                    
                    # Invalidate cache entry if it was None/placeholder
                    keys_to_remove = [k for k in self._icon_cache if k.startswith(f"{language}_")]
                    for k in keys_to_remove:
                        del self._icon_cache[k]
                        
                    self.icon_downloaded.emit(language)
                except Exception as e:
                    logger.error(f"Failed to save icon for {language}: {e}")
        
        reply.deleteLater()
    
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
            # Trigger async download
            self.download_icon(language)
            return None
        
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
    
    def get_download_error(self, language: str) -> Optional[str]:
        """Get download error message for a language if icon failed to download.
        
        Args:
            language: Language name
            
        Returns:
            Error message if download failed, None if icon available or not attempted
        """
        return self._download_errors.get(language)
    
    def clear_cache(self) -> None:
        """Clear the in-memory icon cache and download errors."""
        self._icon_cache.clear()
        self._download_errors.clear()
    
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
                except Exception as e:
                    logger.warning(f"Failed to delete icon {icon_file}: {e}")
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
