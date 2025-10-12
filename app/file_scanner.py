"""File scanner for detecting and grouping code files by language."""
import os
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


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
            
        for root, dirs, files in os.walk(folder):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for filename in files:
                file_path = Path(root) / filename
                ext = file_path.suffix.lower()
                
                if ext in LANGUAGE_MAP:
                    lang = LANGUAGE_MAP[ext]
                    language_files[lang].append(str(file_path))
    
    return dict(language_files)


def get_language_for_file(file_path: str) -> str:
    """Return the language name for a given file path."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "Unknown")
