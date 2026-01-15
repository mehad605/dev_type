# Test Suite Documentation

This document provides a comprehensive overview of the test suite for Dev Type, including what tests exist, their purpose, how they work, and what additional testing is needed for full coverage.

## Overview

The test suite uses **pytest** with approximately **500+ test functions** across **39 test files**. The suite achieves **63% overall code coverage**, with significant variation across modules:

- **High Coverage (>90%)**: `ui_icons.py`, `stats_display.py`, `shortcuts_tab.py`
- **Medium Coverage (60-80%)**: Core business logic modules
- **Low Coverage (<50%)**: Complex UI components like `editor_tab.py`, `stats_tab.py`, `typing_area.py`

## Test Architecture

### Testing Framework
- **Primary**: pytest with fixtures and mocking
- **UI Testing**: PySide6/Qt Test framework for widget interactions
- **Mocking**: `unittest.mock` for external dependencies (sound, icons, databases)
- **Coverage**: pytest-cov for coverage reporting

### Test Organization
Tests are organized by module with clear naming conventions:
- `test_[module].py` - Tests for `app/[module].py`
- Class-based organization for related functionality
- Descriptive test method names explaining what they verify

### Key Fixtures
```python
@pytest.fixture
def app():
    """Qt Application instance for UI tests"""

@pytest.fixture
def db_setup(tmp_path):
    """SQLite database setup for persistence tests"""

@pytest.fixture
def mock_icon_manager():
    """Mock IconManager to avoid network/graphics issues"""

@pytest.fixture
def mock_sound_manager():
    """Mock SoundManager to avoid audio system dependencies"""
```

## Test Categories

### 1. Core Engine Tests (`test_typing_engine.py`)

**Purpose**: Verify the fundamental typing logic and state management.

**Key Tests**:
- `test_typing_state()` - Basic state object validation
- `test_correct_keystroke()` - Character validation and cursor advancement
- `test_incorrect_keystroke()` - Error handling without advancement
- `test_backspace()` - Character deletion functionality
- `test_ctrl_backspace()` - Word-level deletion
- `test_accuracy_calculation()` - WPM and accuracy metrics
- `test_auto_indent()` - Automatic indentation feature
- `test_pause_and_resume()` - Session state management

**How It Works**:
- Creates `TypingEngine` instances with test content
- Simulates keystroke sequences
- Validates state changes and metrics calculation
- Tests edge cases like backspacing past start, auto-indentation

### 2. Settings & Persistence Tests (`test_expanded_settings.py`, `test_stats_db.py`)

**Purpose**: Ensure settings persistence and database operations work correctly.

**Key Tests**:
- `test_color_settings()` - Color preference storage/retrieval
- `test_font_settings()` - Font configuration persistence
- `test_folder_management()` - Project folder tracking
- `test_session_progress()` - Typing session state saving/loading
- `test_record_session_history()` - Historical session logging

**How It Works**:
- Uses temporary SQLite databases
- Tests CRUD operations for all setting types
- Validates data integrity across app restarts
- Tests migration logic for schema changes

### 3. UI Component Tests (`test_ui_main.py`, `test_editor_tab.py`, etc.)

**Purpose**: Verify user interface behavior and interactions.

**Key Tests**:
- `TestMainWindow` - Application window lifecycle
- `TestEditorTab` - File editing and saving functionality
- `TestFoldersTab` - Project folder management UI
- `TestLanguagesTab` - Language detection and statistics UI

**How It Works**:
- Creates Qt application instances
- Builds widget hierarchies with mocked dependencies
- Simulates user interactions (clicks, key presses)
- Validates UI state changes and signals emission

### 4. File System Tests (`test_file_scanner.py`, `test_file_tree.py`)

**Purpose**: Ensure reliable file discovery and organization.

**Key Tests**:
- `test_scan_folders_with_files()` - Language detection in codebases
- `test_scan_folders_ignores_venv()` - Proper exclusion of unwanted directories
- `test_file_tree_widget_initialization()` - UI tree building
- `test_open_random_file_*()` - File selection logic

**How It Works**:
- Creates temporary directory structures
- Scans for various file types and languages
- Validates language detection accuracy
- Tests file tree navigation and selection

### 5. Demo Data Generation Tests (`test_demo_data.py`)

**Purpose**: Verify the demo data generation system works correctly.

**Key Tests**:
- `test_generate_demo_data_creates_records()` - Data creation validation
- `test_generate_demo_data_fields()` - Record structure verification

**How It Works**:
- Generates fake typing sessions with realistic statistics
- Validates database population
- Ensures data integrity for demo/sandbox modes

### 6. Icon System Tests (`test_icon_manager.py`, `test_ui_icons.py`)

**Purpose**: Verify icon loading and rendering systems.

**Key Tests**:
- `test_get_icon_valid()` - Material icon theme lookups
- `test_get_pixmap_valid()` - SVG to pixmap conversion
- `test_icon_caching()` - Performance optimization validation

**How It Works**:
- Tests icon lookup by language/file type
- Validates SVG rendering quality
- Ensures caching prevents redundant operations

### 7. Sound System Tests (`test_sound_manager.py`, `test_sound_*_widget.py`)

**Purpose**: Verify audio feedback functionality.

**Key Tests**:
- `test_sound_manager_init()` - Sound system initialization
- `test_set_volume()` - Volume control functionality
- `test_create_custom_profile()` - Custom sound profile creation

**How It Works**:
- Mocks audio system to avoid actual sound output
- Tests profile loading and switching
- Validates volume and effect controls

### 8. Profile Management Tests (`test_profile_manager.py`)

**Purpose**: Ensure user profile isolation and switching works.

**Key Tests**:
- `test_create_profile()` - New profile creation
- `test_switch_profile()` - Profile switching logic
- `test_delete_profile()` - Profile removal with constraints

**How It Works**:
- Creates isolated profile directories
- Tests profile metadata persistence
- Validates profile switching affects data isolation

## Test Infrastructure

### Mocking Strategy
The test suite heavily uses mocking to isolate components:

```python
@pytest.fixture
def mock_icon_manager():
    """Prevent network requests during tests."""
    with patch('app.languages_tab._get_icon_manager') as mock_getter:
        mock_im = MagicMock()
        mock_im.get_icon.return_value = None
        mock_getter.return_value = mock_im
        yield mock_im
```

### Database Testing
Tests use temporary databases to avoid interfering with user data:

```python
@pytest.fixture
def db_setup(tmp_path):
    db_file = tmp_path / "test.db"
    settings.init_db(str(db_file))
    return db_file
```

### UI Testing
Qt-based UI tests use QApplication fixtures and simulate user interactions:

```python
def test_window_initialization(self, app, mock_icon_manager, mock_sound_manager):
    window = MainWindow()
    assert window.windowTitle() == "Dev Typing App"
```

### Key Test Additions

#### Ghost Race Statistics Tests (`test_editor_tab.py::TestGhostRaceStats`)
**Purpose**: Ensures that typing statistics are correctly updated after ghost races, whether the user wins or loses.

**Test Methods**:
- `test_ghost_race_stats_update_on_loss()`: Verifies that when a user loses a ghost race (takes longer than the ghost), their "last typed" WPM and accuracy are still updated in the database, but the file is not marked as completed.
- `test_ghost_race_stats_update_on_win()`: Verifies that when a user wins a ghost race (completes before the ghost), their stats are updated and the file is marked as completed.

**Why Important**: This prevents data loss for partial typing sessions during competitive gameplay, ensuring users can track their progress even in incomplete races.

#### Ghost Race Data Consistency Tests (`test_editor_tab.py::TestGhostRaceDataConsistency`)
**Purpose**: Ensures that all ghost race data (WPM, accuracy, time, keystroke counts) is properly stored and consistently displayed in the results dialog without recalculation.

**Test Methods**:
- `test_ghost_race_data_storage_and_display_consistency()`: Verifies that race statistics are calculated once during the race, stored correctly in the database, and passed unchanged to the results dialog for display.
- `test_ghost_race_no_recalculation_in_dialog()`: Ensures that the SessionResultDialog displays the exact stats provided to it, without performing any recalculations or modifications.

**Why Important**: Prevents data inconsistencies between what gets stored and what users see, ensuring accurate performance tracking and reliable ghost data for future races.

## Coverage Gaps & Missing Tests

Based on the coverage report, here are the most critical missing test areas:

### High Priority (Low Coverage, High Risk)

#### 1. Editor Tab (`editor_tab.py` - 46% coverage)
**Existing Tests**:
- Ghost race statistics updates (win/loss scenarios) - `TestGhostRaceStats`

**Missing Tests**:
- File loading edge cases (binary files, encoding errors)
- Save functionality and overwrite confirmation dialogs
- Progress tracking during typing sessions
- Race condition handling in session state updates
- Error recovery when database operations fail

**Why Important**:
- Core user workflow (file editing and saving)
- Data loss prevention critical
- Complex state management

#### 2. Stats Tab (`stats_tab.py` - 40% coverage)
**Missing Tests**:
- Chart rendering and data visualization
- Filter application and query generation
- Language filter chip interactions
- Date range filtering logic
- Export functionality

**Why Important**:
- Complex data visualization logic
- User experience for performance tracking
- Database query correctness

#### 3. Typing Area (`typing_area.py` - 44% coverage)
**Missing Tests**:
- Multi-file editing scenarios
- Character encoding edge cases
- Performance with large files (>10MB)
- Real-time syntax highlighting accuracy
- Keyboard shortcut handling

**Why Important**:
- Core typing experience
- Performance bottlenecks
- User input handling reliability

#### 4. UI Main Window (`ui_main.py` - 70% coverage)
**Missing Tests**:
- Profile switching UI workflows
- Settings dialog interactions
- Window state persistence (maximize, position)
- Menu bar functionality
- Drag-and-drop file handling

**Why Important**:
- Main application entry point
- User onboarding experience
- State management across sessions

### Medium Priority

#### 5. Sound Manager (`sound_manager.py` - 46% coverage)
**Missing Tests**:
- Audio device enumeration and selection
- Custom profile creation UI workflows
- Sound loading error handling
- Performance with many custom sounds

#### 6. Portable Data (`portable_data.py` - 47% coverage)
**Missing Tests**:
- Platform-specific path resolution
- Migration from legacy data formats
- Permission error handling
- Data directory conflicts

#### 7. Session Result Dialog (`session_result_dialog.py` - 43% coverage)
**Missing Tests**:
- Statistics calculation accuracy
- Chart rendering with edge case data
- Dialog sizing and layout on different screens
- Save/cancel workflow completeness

## Recommended Test Additions

### 1. Integration Tests
```python
def test_full_typing_workflow():
    """Test complete user journey: load file → type → save stats → view results"""
    # End-to-end workflow validation
```

### 2. Performance Tests
```python
def test_large_file_handling():
    """Test typing area performance with 10MB+ files"""
    # Memory usage, responsiveness validation
```

### 3. Error Recovery Tests
```python
def test_database_corruption_recovery():
    """Test graceful handling of corrupted settings/stats databases"""
    # Data integrity and user experience
```

### 4. Cross-Platform Tests
```python
def test_path_handling_platform_differences():
    """Test file path handling on Windows/macOS/Linux"""
    # Platform compatibility validation
```

### 5. Accessibility Tests
```python
def test_keyboard_navigation():
    """Test full application usability with keyboard-only navigation"""
    # Accessibility compliance
```

## Test Quality Metrics

### Current Status
- **Total Tests**: 502
- **Coverage**: 63%
- **Test Files**: 39
- **Average Tests per File**: ~13

### Quality Indicators
- ✅ **Good**: Comprehensive unit test coverage for core logic
- ✅ **Good**: Proper mocking strategy for external dependencies
- ✅ **Good**: Database isolation prevents test interference
- ⚠️ **Needs Work**: UI component coverage is low
- ⚠️ **Needs Work**: Integration test coverage minimal

## Running Tests

### Basic Test Execution
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_typing_engine.py

# Run specific test
uv run pytest tests/test_typing_engine.py::test_auto_indent
```

### Test Categories
```bash
# Fast unit tests only
uv run pytest -m "not slow"

# UI tests only
uv run pytest tests/test_ui_*.py

# Database tests only
uv run pytest tests/test_*_db.py
```

## Test Development Guidelines

### 1. Test Naming
```python
def test_feature_under_test_condition_expected_result():
    """Clear description of what the test validates."""
```

### 2. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies
- Clean up temporary files

### 3. Test Coverage Goals
- **Core Logic**: >90% coverage
- **UI Components**: >70% coverage
- **Error Paths**: All major error conditions tested
- **Integration**: Key user workflows covered

### 4. Test Maintenance
- Update tests when refactoring code
- Remove obsolete tests promptly
- Document complex test scenarios
- Keep test data realistic but minimal

## Future Testing Improvements

1. **CI/CD Integration**: Automated test runs on commits
2. **Performance Benchmarking**: Track performance regressions
3. **Visual Regression Testing**: UI appearance validation
4. **Load Testing**: High-volume typing session simulation
5. **Accessibility Testing**: Screen reader and keyboard navigation

---

