# Agent Guidelines for Dev-Type

## Build/Lint/Test Commands

### Package Management
- **Primary tool**: `uv` (fast Python package manager)
- **Install dependencies**: `uv sync`
- **Run application**: `uv run main.py`

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_expanded_settings.py`
- **Run specific test function**: `uv run pytest tests/test_expanded_settings.py::test_color_settings`
- **Run tests with coverage**: `uv run pytest --cov=app.ui_main tests/test_ui_main.py --cov-report=term-missing`
- **Verbose output**: `uv run pytest -v`

### Building
- **Windows**: `uv run python build.py --windows --clean`
- **Linux**: `uv run python build.py --linux --clean`
- **Clean build artifacts**: `uv run python build.py --clean`

## Code Style Guidelines

### Imports
- Order: Standard library → Third-party → Local imports
- Separate import groups with blank lines
- Use absolute imports for local modules: `import app.settings as settings`
- Group related imports: `from pathlib import Path, PurePath`

### Formatting & Structure
- **Indentation**: 4 spaces (standard Python)
- **Line length**: Try to keep under 100 characters when practical
- **Blank lines**: Between functions and classes for readability
- **Docstrings**: Triple-quoted strings for modules, classes, and methods
- **Comments**: Minimal; use descriptive names instead

### Type Hints
- Always annotate function signatures: `def process_file(path: str) -> bool:`
- Use Optional for nullable types: `def get_setting(key: str) -> Optional[str]:`
- Import from typing: `from typing import Optional, List, Dict, Set, Tuple, Any`
- Use dataclasses for data containers with type annotations

### Naming Conventions
- **Classes**: PascalCase (e.g., `TypingEngine`, `SoundManager`)
- **Functions/Methods**: snake_case (e.g., `process_keystroke`, `get_setting`)
- **Variables**: snake_case (e.g., `current_profile`, `db_path`)
- **Constants**: UPPER_CASE with underscores (e.g., `MAX_SCAN_DEPTH`, `LANGUAGE_MAP`)
- **Private members**: Prefix with underscore (e.g., `_initialized`, `_load_config()`)
- **Modules**: lowercase with underscores (e.g., `typing_engine.py`)

### Error Handling
- Use module-level logger: `logger = logging.getLogger(__name__)`
- Wrap critical operations in try-except blocks
- Log errors with context: `logger.error(f"Failed to load config: {e}")`
- Return boolean success/failure: `def create_profile(name: str) -> bool:`
- Use Optional return types for operations that may fail
- Validate inputs early; raise ValueError for invalid arguments

### Qt/PySide6 Specific
- Signals defined at class level: `profile_changed = Signal(str)`
- Connect signals with slots: `self.profile_switched.connect(self._on_profile_switch)`
- Use QTimer for delayed operations instead of time.sleep()
- Mock Qt classes in tests using unittest.mock.MagicMock
- Set QT_QPA_PLATFORM=offscreen for headless testing

### Testing Guidelines
- Use pytest with fixtures for setup/teardown
- Use `tmp_path` fixture for temporary files/directories
- Mock external dependencies: `@patch('app.settings.get_setting')`
- Test names should describe what is tested: `test_profile_creation_with_duplicate_name`
- Group related tests in classes for complex modules
- Use `pytest.skip` for platform-specific tests
- Test error paths and edge cases, not just happy paths

### Testing Workflow (Bug Fixes & New Features)
When fixing bugs or adding new features, follow this comprehensive testing and documentation procedure:

1. **Run Tests First**: Always run the full test suite (`uv run pytest`) before making changes to identify any existing issues
2. **Fix Implementation**: Implement the bug fix or new feature
3. **Run Tests Again**: Run tests to identify any broken functionality caused by changes
4. **Fix Broken Tests**: Update existing tests that fail due to legitimate changes in behavior
5. **Add New Tests**: Write comprehensive tests for new features, covering:
   - Happy path functionality
   - Edge cases and error conditions
   - Integration with existing code
   - User interface interactions (for UI features)
6. **Update Documentation**: Update `docs/TESTS.md` with:
   - New test descriptions and purposes
   - Updated test counts
   - Documentation of new testing approaches
7. **Final Verification**: Run complete test suite and verify all tests pass

**VERY IMPORTANT**: When you have completed a task, you MUST run the lint and typecheck commands (e.g. npm run lint, npm run typecheck, ruff, etc.) with Bash if they were provided to you to ensure your code is correct. If you are unable to find the correct command, ask the user for the command to run and if they supply it, proactively suggest writing it to AGENTS.md so that you will know to run it next time.

### Architecture Patterns
- **Singletons**: Use `__new__()` pattern for managers (ProfileManager, SoundManager)
- **Data persistence**: SQLite for settings/stats (app.settings)
- **State management**: Dataclasses for state objects (TypingState)
- **Signals/Slots**: Qt signals for cross-component communication
- **Path handling**: Use pathlib.Path for all file operations
- **Logging**: Structured logging with different levels (debug/info/warning/error)

### Database Operations
- Use SQLite via sqlite3 module
- Initialize DB with `settings.init_db(path)`
- Use context managers for connections: `with sqlite3.connect(db_path) as conn:`
- Use parameterized queries to prevent SQL injection
- Handle database errors gracefully with try-except

### File Operations
- Always use Path objects: `Path(file_path).exists()`
- Create directories with `mkdir(parents=True, exist_ok=True)`
- Handle file encoding explicitly: `open(path, "r", encoding="utf-8")`
- Clean up temporary resources in finally blocks
- Validate file paths before operations (check existence, type, permissions)
