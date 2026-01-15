
"""Icon manager using Material Icon Theme assets."""
import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize, Qt, QObject

from app.settings import get_icons_dir

logger = logging.getLogger(__name__)

class IconManager(QObject):
    """Manages icon retrieval using VS Code Material Icon Theme."""
    
    def __init__(self):
        super().__init__()
        self.icon_dir = get_icons_dir()
        self.manifest_path = self.icon_dir / "icons.json"
        
        self.icon_definitions: Dict[str, str] = {}
        self.file_extensions: Dict[str, str] = {}
        self.file_names: Dict[str, str] = {}
        self.folder_names: Dict[str, str] = {}
        self.folder_names_expanded: Dict[str, str] = {}
        self.language_ids: Dict[str, str] = {}
        self.light_files: Dict[str, str] = {} # For checking if light variant exists
        
        self._cache: Dict[str, QPixmap] = {}
        
        # Import here to avoid potential circular imports at module level if file_scanner changes later
        from app.file_scanner import LANGUAGE_MAP
        self.language_map = LANGUAGE_MAP
        
        # Build inverse map: Language Name -> [extensions]
        self.name_to_exts: Dict[str, list] = {}
        for ext, name in self.language_map.items():
            if name not in self.name_to_exts:
                self.name_to_exts[name] = []
            self.name_to_exts[name].append(ext)
        
        self._load_manifest()

    def _load_manifest(self):
        """Load the icons.json manifest."""
        if not self.manifest_path.exists():
            logger.error(f"Icon manifest not found at {self.manifest_path}")
            return

        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 1. Parse Definitions
            # "iconDefinitions": { "javascript": { "iconPath": "./../icons/javascript.svg" } }
            defs = data.get("iconDefinitions", {})
            for icon_id, props in defs.items():
                path_str = props.get("iconPath", "")
                # Extract filename "javascript.svg" from "./../icons/javascript.svg"
                filename = os.path.basename(path_str)
                self.icon_definitions[icon_id] = filename

            # 2. Parse Mappings
            self.file_extensions = data.get("fileExtensions", {})
            self.file_names = data.get("fileNames", {})
            self.folder_names = data.get("folderNames", {})
            self.folder_names_expanded = data.get("folderNamesExpanded", {}) # Some themes have this
            self.language_ids = data.get("languageIds", {})
            
            # Map common language names to their IDs if missing
            # This helps bridging the gap between our app's "Python" and the theme's "python"
            self._ensure_language_mappings()

            logger.info(f"Loaded {len(self.icon_definitions)} icons from manifest")

        except Exception as e:
            logger.error(f"Failed to load icon manifest: {e}")

    def _ensure_language_mappings(self):
        """Add manual mappings for known language names to IDs."""
        # The theme usually uses lowercase IDs.
        # Our app uses Capitalized names (Python, Rust).
        # We can also rely on lowercasing the input request.
        pass

    def _get_pixmap_from_svg(self, filename: str, size: int) -> Optional[QPixmap]:
        """Render SVG to QPixmap."""
        if not filename:
            return None
            
        cache_key = f"{filename}_{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        path = self.icon_dir / filename
        if not path.exists():
            return None
            
        renderer = QSvgRenderer(str(path))
        if not renderer.isValid():
            return None
            
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        
        self._cache[cache_key] = pixmap
        return pixmap

    def get_icon(self, language: str, size: int = 48) -> Optional[QPixmap]:
        """Legacy compatibility: Get icon by Language Name (e.g. "Python")."""
        # Try finding ID in language_ids
        # 1. Try exact match
        icon_id = self.language_ids.get(language)
        
        # 2. Try lower case match
        if not icon_id:
            icon_id = self.language_ids.get(language.lower())
            
        # 3. If no mapping, try to use the language name as the icon ID directly
        if not icon_id:
            # Check if an icon definition exists with this name
            if language.lower() in self.icon_definitions:
                icon_id = language.lower()
                
        # 4. Fallback: try looking up extension
        if not icon_id:
            candidates = []
            # Try extensions from language map (e.g. "Text" -> ".txt")
            if language in self.name_to_exts:
                candidates.extend([ext.lstrip(".") for ext in self.name_to_exts[language]])
            
            # Try language name as extension (e.g. "Env" -> "env", "Spec" -> "spec")
            candidates.append(language.lower())
            
            for ext in candidates:
                if ext in self.file_extensions:
                    icon_id = self.file_extensions[ext]
                    break

        if icon_id:
            filename = self.icon_definitions.get(icon_id)
            return self._get_pixmap_from_svg(filename, size)
            
        # Default fallback
        return self._get_pixmap_from_svg("file.svg", size)

    def get_file_icon(self, filename: str, size: int = 16) -> QPixmap:
        """Get icon for a specific file (e.g. 'package.json', 'script.py')."""
        name = filename.lower()
        
        # 1. Check exact filename
        icon_id = self.file_names.get(name)
        
        # 2. Check extensions
        if not icon_id:
            parts = name.split(".")
            if len(parts) > 1:
                # Try compound extension (e.g. .test.tsx) - logic simplified here
                ext = parts[-1]
                icon_id = self.file_extensions.get(ext)
                
                # Try long extension if no short one found? (e.g. .d.ts)
                # Material Theme usually handles this in the generation or keys
                
        # 3. Fallback: check language map
        if not icon_id:
            ext = "." + parts[-1] if len(parts) > 1 else ""
            if ext and ext in self.language_map:
                language_name = self.language_map[ext]
                # Delegate to get_icon which handles language IDs
                return self.get_icon(language_name, size)
            
        # 4. Default
        if not icon_id:
            icon_id = "file"
            
        svg_file = self.icon_definitions.get(icon_id)
        pm = self._get_pixmap_from_svg(svg_file, size)
        if pm: return pm
        return QPixmap()

    def get_folder_icon(self, foldername: str, is_open: bool = False, size: int = 16) -> QPixmap:
        """Get icon for a folder."""
        name = foldername.lower()
        
        # 1. Check specific folder name (e.g. 'src', 'test')
        if is_open:
            # We assume expanded keys might exist or we suffix
            # Material theme usually has separate keys or logic
            # For simplicity: check folderNames for base ID, then append '-open' if valid
            pass
            
        # Material Theme logic:
        # folderNames["src"] = "folder-src"
        # iconDefinitions["folder-src"] -> "folder-src.svg"
        # iconDefinitions["folder-src-open"] -> "folder-src-open.svg"
        
        icon_id = self.folder_names.get(name)
        if not icon_id:
            icon_id = "folder"
            
        if is_open:
            # Try to find corresponding open version
            open_id = f"{icon_id}-open"
            if open_id in self.icon_definitions:
                icon_id = open_id
            else:
                # Fallback to generic open
                icon_id = "folder-open"
                
        svg_file = self.icon_definitions.get(icon_id)
        pm = self._get_pixmap_from_svg(svg_file, size)
        if pm: return pm
        return QPixmap()

    def get_download_error(self, language: str) -> Optional[str]:
        return None # No downloading anymore

# Global instance
_icon_manager = None

def get_icon_manager() -> IconManager:
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager
