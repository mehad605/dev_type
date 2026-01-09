"""File scanner for detecting and grouping code files by language."""
import logging
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import fnmatch
import app.settings as settings

logger = logging.getLogger(__name__)

# Maximum directory depth to prevent infinite recursion from symlink loops
MAX_SCAN_DEPTH = 50

# Maximum number of files to scan per folder (prevent memory issues)
MAX_FILES_PER_FOLDER = 50000


# Language definitions: extension -> language name mapping

# Dynamic extension registration will happen in code
# Initial known mappings
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
}
# We will no longer hardcode the full list here. 
# Instead, we will rely on a more dynamic approach or a larger default map if needed.
# But for the user request "completely remove hardcoded list", 
# we should switch to a mechanism that infers or learns.
# HOWEVER, for file extensions to names, we usually NEED a mapping.
# Maybe the user means "don't just STRICTLY limit to this list".
# Let's keep a default list but ALLOW unknown extensions to become "languages".

# Updated approach:
# 1. Keep a robust default list (it's useful!)
# 2. But if we encounter an unknown extension, we use the extension itself as the "Language" name
#    (e.g., .bf -> "bf", .xyz -> "xyz")
# 3. This effectively "removes the limit" of the hardcoded list.

# Standard languages (keep for nice naming)
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
    ".bf": "Brainfuck", # Per user request example
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


class IgnoreManager:
    """Optimized manager for checking if paths should be ignored."""
    
    def __init__(self, ignored_files: List[str], ignored_folders: List[str]):
        # Files/Patterns
        self.file_exts: Set[str] = set()
        self.file_names: Set[str] = set()
        self.file_paths: Set[str] = set()
        self.file_globs: List[Tuple[str, bool, bool]] = [] # (pattern, is_path, is_case_insensitive)
        
        # Folders
        self.folder_names: Set[str] = set()
        self.folder_paths: Set[str] = set()
        self.folder_globs: List[Tuple[str, bool, bool]] = []
        
        for p in ignored_files:
            self._add_pattern(p, is_folder=False)
        for p in ignored_folders:
            self._add_pattern(p, is_folder=True)

    def _add_pattern(self, pattern: str, is_folder: bool):
        is_case_insensitive = pattern.startswith('"') and pattern.endswith('"')
        orig_p = pattern[1:-1] if is_case_insensitive else pattern
        p = orig_p.lower() if is_case_insensitive else orig_p
        
        is_path = "\\" in orig_p or "/" in orig_p
        has_wildcard = '*' in orig_p or '?' in orig_p
        
        # 1. Optimized Extension Check: *.exe (no other wildcards)
        if not is_folder and p.startswith("*.") and not is_path:
            rest = p[2:]
            if '*' not in rest and '?' not in rest:
                self.file_exts.add(p[1:]) # .exe
                return

        # 2. Exact Match (No Wildcards)
        if not has_wildcard:
            if is_path:
                if is_folder: self.folder_paths.add(p)
                else: self.file_paths.add(p)
            else:
                if is_folder: self.folder_names.add(p)
                else: self.file_names.add(p)
            return

        # 3. Glob Match (fallback)
        if is_folder:
            self.folder_globs.append((p, is_path, is_case_insensitive))
        else:
            self.file_globs.append((p, is_path, is_case_insensitive))

    def should_ignore_file(self, path: Path) -> bool:
        name = path.name
        ext = path.suffix.lower()
        if ext in self.file_exts:
            return True
            
        name_lower = name.lower()
        if name in self.file_names or name_lower in self.file_names:
            return True
            
        str_path = str(path)
        str_path_lower = str_path.lower()
        if str_path in self.file_paths or str_path_lower in self.file_paths:
            return True
            
        for p, is_path, is_ci in self.file_globs:
            to_check = (str_path_lower if is_ci else str_path) if is_path else (name_lower if is_ci else name)
            if is_ci:
                if fnmatch.fnmatch(to_check, p): return True
            else:
                if fnmatch.fnmatchcase(to_check, p): return True
        return False

    def should_ignore_folder(self, path: Path) -> bool:
        name = path.name
        name_lower = name.lower()
        if name in self.folder_names or name_lower in self.folder_names:
            return True
            
        str_path = str(path)
        str_path_lower = str_path.lower()
        if str_path in self.folder_paths or str_path_lower in self.folder_paths:
            return True
            
        for p, is_path, is_ci in self.folder_globs:
            to_check = (str_path_lower if is_ci else str_path) if is_path else (name_lower if is_ci else name)
            if is_ci:
                if fnmatch.fnmatch(to_check, p): return True
            else:
                if fnmatch.fnmatchcase(to_check, p): return True
        return False


def get_global_ignore_settings() -> Tuple[List[str], List[str]]:
    """Return (ignored_files, ignored_folders) from settings."""
    raw_files = settings.get_setting("ignored_files", settings.get_default("ignored_files"))
    raw_folders = settings.get_setting("ignored_folders", settings.get_default("ignored_folders"))
    
    ignored_files = [p.strip() for p in raw_files.split('\n') if p.strip()]
    ignored_folders = [p.strip() for p in raw_folders.split('\n') if p.strip()]
    
    return ignored_files, ignored_folders


def should_ignore_file(path: Path, ignored_files: List[str]) -> bool:
    """Check if a file should be ignored based on name or path patterns (Legacy wrapper)."""
    manager = IgnoreManager(ignored_files, [])
    return manager.should_ignore_file(path)


def should_ignore_folder(path: Path, ignored_folders: List[str]) -> bool:
    """Check if a folder should be ignored based on patterns (Legacy wrapper)."""
    manager = IgnoreManager([], ignored_folders)
    return manager.should_ignore_folder(path)


def scan_folders(folder_paths: List[str]) -> Dict[str, List[str]]:
    """
    Scan multiple folders and group files by language.
    
    Args:
        folder_paths: List of folder paths to scan
        
    Returns:
        Dict mapping language name -> list of file paths
    """
    ignored_dirs_set = get_ignored_dirs()
    ignored_file_patterns, ignored_folder_patterns = get_global_ignore_settings()
    ignore_manager = IgnoreManager(ignored_file_patterns, ignored_folder_patterns)
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
            # 1. Hardcoded defaults
            dirs[:] = [d for d in dirs if d not in ignored_dirs_set]
            
            # 2. Also filter out symlinked directories to prevent loops
            dirs[:] = [d for d in dirs if not (root_path / d).is_symlink()]

            # 3. User-defined global folder patterns
            dirs[:] = [d for d in dirs if not ignore_manager.should_ignore_folder(root_path / d)]
            
            for filename in files:
                # Check file count limit
                if file_count >= MAX_FILES_PER_FOLDER:
                    logger.warning(f"Max files limit ({MAX_FILES_PER_FOLDER}) reached for folder: {folder_path}")
                    break
                
                file_path = root_path / filename
                
                # Skip symlinked files (could point outside folder)
                if file_path.is_symlink():
                    continue
                
                # Global ignore check (patterns)
                if ignore_manager.should_ignore_file(file_path):
                    continue
                
                ext = file_path.suffix.lower()
                
                # Dynamic Language Detection
                if ext in LANGUAGE_MAP:
                    lang = LANGUAGE_MAP[ext]
                elif ext: # If it has an extension and we don't know it
                    # Auto-register: capitalize extension
                    lang = ext.lstrip(".").capitalize()
                else:
                    lang = "No Extension"
                
                language_files[lang].append(str(file_path))
                file_count += 1
            
            if file_count >= MAX_FILES_PER_FOLDER:
                break
    
    return dict(language_files)


def get_language_for_file(file_path: str) -> str:
    """Return the language name for a given file path."""
    ext = Path(file_path).suffix.lower()
    """Return the language name for a given file path."""
    ext = Path(file_path).suffix.lower()
    if ext in LANGUAGE_MAP:
        return LANGUAGE_MAP[ext]
    return ext.lstrip(".").capitalize() if ext else "Unknown"
