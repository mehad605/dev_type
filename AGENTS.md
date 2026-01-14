# AGENTS.md

This file contains guidelines and commands for agentic coding agents working on the Dev Type project.

## Project Overview

Dev Type is a modern typing practice application built with Python 3.13+ and PySide6 (Qt). It allows developers to practice typing on real code files from their projects, with comprehensive statistics tracking, ghost replays, and customizable themes.

## Build/Test Commands

### Environment Setup
```bash
# Using uv (recommended)
uv sync
uv run main.py

# Using pip
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install .
python main.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_typing_engine.py

# Run single test function
uv run pytest tests/test_typing_engine.py::TestTypingEngine::test_wpm_calculation

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run tests with verbose output
uv run pytest -v
```

### Building
```bash
# Build for current platform
uv run python build.py

# Build Windows executable
uv run python build.py --windows --clean

# Build Linux .deb package
uv run python build.py --linux --clean

# Build for all platforms
uv run python build.py --all
```

### Running the Application
```bash
# Normal run
uv run main.py

# Demo mode with fake statistics
uv run main.py --demo

# Demo mode with specific year data
uv run main.py --demo --year 2025

# Demo mode with persistent data
uv run main.py --demo --persist
```

## Code Style Guidelines

### Import Organization
- Standard library imports first
- Third-party imports next (PySide6, pytest, etc.)
- Local application imports last (app.* modules)
- Use `from typing import Optional, List, Dict` for type hints
- Group related imports together

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict

# Third-party
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal
import pytest
from unittest.mock import MagicMock

# Local imports
from app.typing_engine import TypingState
from app.settings import get_setting
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `TypingEngine`, `FolderCardWidget`)
- **Functions/Methods**: snake_case (e.g., `process_keystroke`, `get_setting`)
- **Variables**: snake_case (e.g., `cursor_position`, `elapsed_time`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SETTING_DEFAULTS`, `DEBUG_STARTUP_TIMING`)
- **Private members**: Prefix with underscore (e.g., `_list_widget`, `_selected`)

### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable values
- Use `List[T]`, `Dict[K, V]` for collections
- Use `Union[T, U]` when multiple types are possible

```python
def calculate_wpm(self, elapsed_time: float) -> float:
    """Calculate words per minute."""
    if elapsed_time <= 0:
        return 0.0
    return (self.correct_keystrokes / 5) / (elapsed_time / 60)

def get_folders(self) -> List[str]:
    """Get list of folder paths."""
    return self._folders

def set_setting(self, key: str, value: Optional[str]) -> None:
    """Set a configuration value."""
    if value is not None:
        self._settings[key] = value
```

### Error Handling
- Use specific exception types when possible
- Log errors with context information
- Use try/except blocks for external dependencies
- Return None or default values for non-critical errors

```python
try:
    from app.portable_data import get_data_dir
    _PORTABLE_MODE_AVAILABLE = True
except ImportError:
    _PORTABLE_MODE_AVAILABLE = False
    def get_data_dir():
        return None
```

### Documentation
- Use docstrings for all classes and public methods
- Follow Google-style or NumPy-style docstring format
- Include parameter types and return values
- Add brief description of functionality

```python
class TypingEngine:
    """Handles typing logic and state management.
    
    This class processes keystrokes, calculates statistics, and manages
    the overall typing session state.
    """
    
    def process_keystroke(self, char: str, expected: str) -> bool:
        """Process a single keystroke and update state.
        
        Args:
            char: The typed character.
            expected: The expected character at current position.
            
        Returns:
            True if the keystroke was correct, False otherwise.
        """
        pass
```

### Qt/PySide6 Guidelines
- Use proper signal/slot connections with type hints
- Set object names for widgets that need styling
- Use layouts instead of fixed positioning
- Clean up resources in destructors if needed

```python
class CustomWidget(QWidget):
    """Custom widget with proper signal handling."""
    
    # Define signals with type hints
    value_changed = Signal(int)
    error_occurred = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("customWidget")
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        # ... widget setup
```

### Testing Guidelines
- Use descriptive test method names
- Mock external dependencies (file system, network, Qt)
- Use fixtures for common test setup
- Test both success and failure cases
- Use parametrized tests for multiple scenarios

```python
class TestTypingEngine:
    """Test cases for TypingEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a test typing engine."""
        return TypingEngine("test content")
    
    def test_wpm_calculation(self, engine):
        """Test WPM calculation with valid input."""
        engine.correct_keystrokes = 100
        engine.elapsed_time = 60.0
        assert engine.wpm() == 20.0
    
    @pytest.mark.parametrize("input_char,expected,result", [
        ("a", "a", True),
        ("b", "a", False),
        ("", "a", False),
    ])
    def test_process_keystroke(self, engine, input_char, expected, result):
        """Test keystroke processing with various inputs."""
        assert engine.process_keystroke(input_char, expected) == result
```

### File Organization
- Keep related functionality in the same module
- Use `app/` package for application code
- Use `tests/` package for test code
- Separate UI components from business logic
- Use `__init__.py` files for clean imports

### Constants and Configuration
- Define all setting defaults in `app/settings.py`
- Use the `SETTING_DEFAULTS` dictionary as single source of truth
- Access settings through `get_setting()` and `set_setting()` functions
- Use environment variables for build-time configuration

### Performance Considerations
- Use lazy imports for heavy dependencies
- Cache expensive computations
- Use Qt's built-in optimizations (signals/slots, lazy loading)
- Profile startup time with `DEBUG_STARTUP_TIMING` flag

### Security Notes
- Never commit secrets or API keys
- Validate user input before processing
- Use proper file path handling to prevent directory traversal
- Sanitize data before database operations

## Development Workflow

1. **Before coding**: Run existing tests to ensure baseline
2. **During development**: Write tests alongside new features
3. **Before committing**: Run full test suite and check coverage
4. **After changes**: Test the application manually if UI changes

## Common Patterns

### Database Operations
```python
from app.settings import get_database_path

def get_stats():
    """Get typing statistics from database."""
    db_path = get_database_path()
    if not db_path or not db_path.exists():
        return {}
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stats")
        return dict(cursor.fetchall())
```

### Qt Signal Connections
```python
# Connect signals with proper type checking
self.button.clicked.connect(self._on_button_click)
self.text_field.textChanged.connect(self._on_text_changed)

# Use lambda for passing arguments
self.action.triggered.connect(lambda: self._handle_action("save"))
```

### Mock Dependencies in Tests
```python
@patch('app.languages_tab._get_icon_manager')
def test_language_display(self, mock_getter):
    """Test language display with mocked icon manager."""
    mock_manager = MagicMock()
    mock_manager.get_icon.return_value = None
    mock_getter.return_value = mock_manager
    
    # Test implementation
    pass
```

## Notes for Agents

- This is a desktop application using PySide6/Qt
- The main entry point is `main.py` with splash screen support
- All application code is in the `app/` package
- Tests are in the `tests/` package using pytest
- The project uses SQLite for data persistence
- Build system creates standalone executables for distribution
- No linting/formatting tools are currently configured (feel free to add them)
- Focus on maintaining compatibility with Python 3.13+