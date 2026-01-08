"""File scanner for detecting and grouping code files by language."""
import logging
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# Maximum directory depth to prevent infinite recursion from symlink loops
MAX_SCAN_DEPTH = 50

# Maximum number of files to scan per folder (prevent memory issues)
MAX_FILES_PER_FOLDER = 50000


# Language definitions: extension -> language name mapping
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".m": "Objective-C",
    ".scala": "Scala",
    ".r": "R",
    ".dart": "Dart",
    ".lua": "Lua",
    ".pl": "Perl",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".fish": "Fish",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".txt": "Text",
}


def get_ignored_dirs() -> Set[str]:
    """Return set of directory names to ignore during scanning."""
    return {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "build",
        "dist",
        ".egg-info",
        "target",  # Rust/Java
        "bin",
        "obj",  # C#
    }


def _is_safe_path(path: Path, root: Path) -> bool:
    """Check if a path is safe (within root, not escaping via traversal).
    
    Args:
        path: Path to validate
        root: Root folder that should contain the path
        
    Returns:
        True if path is safe to use, False otherwise
    """
    try:
        # Resolve to absolute path (follows symlinks)
        resolved = path.resolve()
        root_resolved = root.resolve()
        
        # Check path is within root (prevents directory traversal)
        try:
            resolved.relative_to(root_resolved)
            return True
        except ValueError:
            logger.warning(f"Path escapes root folder: {path}")
            return False
    except (OSError, RuntimeError) as e:
        # RuntimeError can occur with symlink loops on some systems
        logger.warning(f"Cannot resolve path {path}: {e}")
        return False


def validate_file_path(file_path: str, root_folder: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate a file path for safety.
    
    Args:
        file_path: Path to validate
        root_folder: Optional root folder the path should be within
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)
    
    # Check for UNC paths on Windows (can hang or be slow)
    if os.name == 'nt' and file_path.startswith('\\\\'):
        return False, "UNC network paths are not supported"
    
    # Check path exists
    try:
        if not path.exists():
            return False, "File does not exist"
    except (OSError, PermissionError) as e:
        return False, f"Cannot access path: {e}"
    
    # Check it's a file, not a directory
    if not path.is_file():
        return False, "Path is not a file"
    
    # Check path is within root if specified
    if root_folder:
        root = Path(root_folder)
        if not _is_safe_path(path, root):
            return False, "File is outside the allowed folder"
    
    return True, None


def scan_folders(folder_paths: List[str]) -> Dict[str, List[str]]:
    """
    Scan multiple folders and group files by language.
    
    Args:
        folder_paths: List of folder paths to scan
        
    Returns:
        Dict mapping language name -> list of file paths
    """
    ignored_dirs = get_ignored_dirs()
    language_files: Dict[str, List[str]] = defaultdict(list)
    
    for folder_path in folder_paths:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            continue
        
        # Track visited directories to detect symlink loops
        seen_inodes: Set[tuple] = set()
        file_count = 0
        
        try:
            folder.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Cannot resolve folder path {folder_path}: {e}")
            continue
        
        for root, dirs, files in os.walk(folder, followlinks=False):
            root_path = Path(root)
            
            # Check scan depth to prevent runaway recursion
            try:
                depth = len(root_path.relative_to(folder).parts)
                if depth > MAX_SCAN_DEPTH:
                    logger.warning(f"Max scan depth reached at: {root}")
                    dirs[:] = []  # Don't recurse deeper
                    continue
            except ValueError:
                continue
            
            # Check for symlink loops via inode tracking
            try:
                stat_info = root_path.stat()
                inode_key = (stat_info.st_dev, stat_info.st_ino)
                if inode_key in seen_inodes:
                    logger.warning(f"Symlink loop detected at: {root}")
                    dirs[:] = []  # Don't recurse into loop
                    continue
                seen_inodes.add(inode_key)
            except (OSError, PermissionError):
                pass
            
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            # Also filter out symlinked directories to prevent loops
            dirs[:] = [d for d in dirs if not (root_path / d).is_symlink()]
            
            for filename in files:
                # Check file count limit
                if file_count >= MAX_FILES_PER_FOLDER:
                    logger.warning(f"Max files limit ({MAX_FILES_PER_FOLDER}) reached for folder: {folder_path}")
                    break
                
                file_path = root_path / filename
                
                # Skip symlinked files (could point outside folder)
                if file_path.is_symlink():
                    continue
                
                ext = file_path.suffix.lower()
                
                if ext in LANGUAGE_MAP:
                    lang = LANGUAGE_MAP[ext]
                    language_files[lang].append(str(file_path))
                    file_count += 1
            
            if file_count >= MAX_FILES_PER_FOLDER:
                break
    
    return dict(language_files)


def get_language_for_file(file_path: str) -> str:
    """Return the language name for a given file path."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "Unknown")
