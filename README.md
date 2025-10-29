# ⌨️ Dev Typing App

> **Practice typing on real code to become a faster developer**

A modern, feature-rich typing practice application specifically designed for programmers. Improve your typing speed and accuracy by practicing on actual code files in your favorite programming languages.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![Qt](https://img.shields.io/badge/Qt-PySide6-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey.svg)

</div>

---

## 📋 Table of Contents

- [What is Dev Typing App?](#-what-is-dev-typing-app)
- [Key Features](#-key-features)
- [Screenshots](#-screenshots)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
- [Technologies Used](#-technologies-used)
- [Architecture Overview](#-architecture-overview)
- [Performance Optimizations](#-performance-optimizations)
- [Development](#-development)
- [Testing](#-testing)
- [Building Executables](#-building-executables)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 What is Dev Typing App?

**Dev Typing App** helps developers improve their typing speed and accuracy by practicing on **real code files** instead of random text. It's like a typing tutor specifically designed for programmers.

### Why Practice on Code?

- **Real-world context**: Practice typing the symbols, brackets, and syntax you use daily
- **Language-specific**: Different languages have different typing patterns (Python vs C++ vs JavaScript)
- **Build muscle memory**: Get faster at typing common code patterns
- **Track progress**: See your WPM improve over time on different languages

### Who is it for?

- 🎓 **Beginners**: Learn to type code without looking at the keyboard
- 💼 **Professionals**: Increase productivity by typing faster
- 🎯 **Speed enthusiasts**: Challenge yourself to beat your personal records
- 👨‍💻 **Polyglot programmers**: Practice typing in multiple programming languages

---

## ✨ Key Features

### 🎨 **Beautiful, Customizable Interface**
- **4 Built-in Themes**: Nord (default), Catppuccin, Dracula dark schemes + Light mode
- **Instant Theme Switching**: No restart required - themes apply immediately
- **Full Color Customization**: Customize every color (correct/incorrect text, cursor, highlights)
- **Font Options**: Choose from popular monospace fonts (Consolas, Fira Code, JetBrains Mono, etc.)
- **Flexible Cursor**: Blinking/static, block/underscore/I-beam styles
- **Smooth Splash Screen**: Professional loading screen with status updates

### 📁 **Smart File Management**
- **Multi-Folder Support**: Add multiple folders containing your code files
- **Automatic Language Detection**: Files are grouped by programming language (Python, JavaScript, Java, C++, etc.)
- **Language Statistics**: See file count and average WPM per language
- **File Tree View**: Browse files with Best WPM and Last WPM columns
- **Incomplete Session Highlighting**: Resume unfinished files easily

### ⌨️ **Advanced Typing Practice**
- **Character-by-Character Validation**: Real-time feedback with color coding
- **Live Statistics**: WPM, accuracy, time, and keystroke breakdown with percentages
- **Auto-Pause**: Session pauses after customizable seconds of inactivity
- **Session Persistence**: Resume incomplete typing sessions automatically
- **Smart Backspace**: Delete character or entire word (Ctrl+Backspace)
- **Visual Feedback**: Green for correct, red for incorrect characters
- **Special Characters**: Space→`␣`, Enter→`⏎`, Tab→4 spaces (customizable space char)

### 📊 **Comprehensive Statistics**
- **Real-time Metrics**: WPM, accuracy percentage, elapsed time
- **Keystroke Breakdown**: Correct(80%), Incorrect(20%), Total(100%)
- **Historical Data**: Best and last WPM for each file
- **Session History**: Filter and view past typing sessions by language, file, WPM, duration
- **Progress Tracking**: See improvement over time

### 💾 **Data Management**
- **SQLite Database**: Fast, reliable local storage
- **Export/Import Settings**: Backup and restore all settings as JSON
- **Export/Import Data**: Backup and restore typing statistics and progress
- **Settings Persistence**: All preferences saved automatically
- **Offline First**: Works completely offline once set up

### ⚡ **Performance Optimizations**
- **Fast Startup**: ~0.7s startup time (4.4x improvement from original 2.9s)
- **Lazy Loading**: Heavy tabs load on-demand
- **Pre-warmed UI Engine**: Stylesheet engine initialized early
- **Deferred Theme Application**: Non-blocking theme loading
- **Optimized Rendering**: Minimal redraws, efficient widget updates

---

## 📸 Screenshots

*[Screenshots showing the interface, typing in action, themes, etc.]*

---

## 🚀 Quick Start

Get up and running in 5 minutes!

### For Novice Users

1. **Install uv** (Python package manager):
   - **Windows**: Download from [uv releases](https://github.com/astral-sh/uv/releases) or use PowerShell:
     ```powershell
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - **Linux/Mac**: Run in terminal:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. **Get the code**:
   ```bash
   git clone https://github.com/yourusername/dev_type.git
   cd dev_type
   ```

3. **Install dependencies** (automatic):
   ```bash
   uv sync
   ```
   This creates a virtual environment and installs everything you need.

4. **Run the app**:
   ```bash
   uv run main.py
   ```
   That's it! The app will open with a splash screen.

5. **Try it out**:
   - Click **"+ Add Folder"** in the Folders tab
   - Select the `demo_files/` folder (included in the project)
   - Go to **Languages** tab
   - Click on **Python** or **JavaScript**
   - Select a file from the file tree
   - **Start typing!** The session begins automatically

### For Experienced Users

```bash
# Quick setup
git clone <repository-url> && cd dev_type && uv sync && uv run main.py
```

---

## 🛠️ Technologies Used

### Core Technologies

| Technology | Version | Purpose | Why We Chose It |
|-----------|---------|---------|-----------------|
| **Python** | 3.13+ | Programming language | Modern features, excellent ecosystem, cross-platform |
| **PySide6 (Qt6)** | 6.10.0+ | GUI framework | Native look, high performance, cross-platform, rich widget set |
| **SQLite** | Built-in | Database | Embedded, zero-config, fast, reliable for local data |
| **uv** | Latest | Package manager | 10-100x faster than pip, automatic venv management |
| **pytest** | 8.4.2+ | Testing framework | Simple, powerful, excellent for unit testing |

### Architecture Pattern

- **MVC-like separation**: Business logic (typing engine, file scanner) separated from UI
- **Signal-slot pattern**: Qt's event-driven architecture for responsive UI
- **Lazy loading**: Heavy components loaded on-demand for fast startup
- **Database-backed settings**: Persistent storage with SQLite for reliability

### Key Libraries & Modules

#### GUI Components (`PySide6.QtWidgets`)
- `QMainWindow`: Main application window with menu bar and central widget
- `QTabWidget`: Tabbed interface for Folders, Languages, History, Typing, Settings
- `QListWidget`: Folder list, language cards (custom widgets)
- `QTreeWidget`: File tree with hierarchical structure
- `QTextEdit`: Typing area with syntax highlighting and color coding
- `QTableWidget`: Session history with sortable columns
- `QLabel`, `QPushButton`, `QComboBox`, etc.: Standard UI controls

#### Core Qt Modules
- `PySide6.QtCore`: Timer (auto-pause), signals/slots (events), file I/O
- `PySide6.QtGui`: Fonts, colors, keyboard events, cursor styles
- `PySide6.QtWidgets`: All UI widgets and layouts

#### Standard Python Libraries
- `sqlite3`: Database operations (settings, stats, history)
- `pathlib`: Cross-platform file path handling
- `json`: Settings/data export/import
- `datetime`: Timestamp formatting
- `time`: Performance timing
- `typing`: Type hints for better code quality

### Design Patterns Used

1. **Singleton Pattern**: Settings and database connections
2. **Observer Pattern**: Qt signals/slots for component communication
3. **Strategy Pattern**: Different color schemes/themes
4. **Factory Pattern**: Widget creation (stats boxes, keystroke displays)
5. **Lazy Initialization**: Deferred loading of expensive components

---

## 📁 Architecture Overview

### Project Structure

```
dev_type/
├── app/                          # Main application package
│   ├── __init__.py              
│   ├── settings.py              # 🗄️ SQLite-backed settings (theme, colors, fonts, cursor)
│   ├── stats_db.py              # 📊 Statistics database (WPM, accuracy, history)
│   ├── file_scanner.py          # 🔍 Language detection and file discovery
│   ├── typing_engine.py         # ⚙️ Core typing logic (NO GUI - pure business logic)
│   ├── themes.py                # 🎨 Theme system (Nord, Catppuccin, Dracula, Light)
│   ├── typing_area.py           # ⌨️ Typing area widget with color coding
│   ├── stats_display.py         # 📈 Live statistics display (WPM, accuracy, keystrokes)
│   ├── file_tree.py             # 🌳 File tree widget with WPM columns
│   ├── editor_tab.py            # 📝 Typing tab (file tree + typing area + stats)
│   ├── languages_tab.py         # 🌐 Languages tab with language cards
│   ├── history_tab.py           # 📜 Session history with filtering
│   └── ui_main.py               # 🪟 Main window, tabs, splash screen
│
├── tests/                        # 🧪 Comprehensive test suite
│   ├── test_settings_db.py      # Settings CRUD operations
│   ├── test_stats_db.py         # Statistics and history tracking
│   ├── test_file_scanner.py     # Language detection algorithms
│   ├── test_typing_engine.py    # Typing logic, WPM, accuracy calculations
│   ├── test_themes.py           # Theme color schemes
│   └── test_expanded_settings.py # Settings persistence
│
├── demo_files/                   # 📂 Sample code files for testing
│   ├── demo.py                  # Python examples
│   └── demo.js                  # JavaScript examples
│
├── main.py                       # 🚀 Application entry point
├── pyproject.toml               # 📦 Dependencies and project config (uv)
├── uv.lock                      # 🔒 Locked dependency versions
└── README.md                    # 📖 This file
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Main Window (QMainWindow)            │
│  ┌───────────────────────────────────────────────────┐  │
│  │              QTabWidget (5 tabs)                   │  │
│  │  ┌──────┬──────────┬─────────┬────────┬─────────┐ │  │
│  │  │Folders│Languages│ History │ Typing │Settings │ │  │
│  │  └──────┴──────────┴─────────┴────────┴─────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                 │                  │
         ▼                 ▼                  ▼
   ┌──────────┐    ┌──────────────┐   ┌──────────────┐
   │ settings │    │  stats_db    │   │file_scanner  │
   │  (SQLite)│    │  (SQLite)    │   │ (scanning)   │
   └──────────┘    └──────────────┘   └──────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ typing_engine   │  ← Pure logic, no GUI
                  │ (WPM, accuracy) │
                  └─────────────────┘
```

### Data Flow

```
User Action → Qt Event → Widget Handler → Business Logic → Database
                                           ↓
                                    Signal Emitted
                                           ↓
                              UI Components Updated
```

**Example: Typing a character**
1. User presses 'a' → `QKeyEvent` fired
2. `TypingAreaWidget.keyPressEvent()` catches event
3. Calls `typing_engine.process_keystroke('a')`
4. Engine updates state (correct/incorrect, position, time)
5. Engine calculates new WPM and accuracy
6. Widget emits `stats_updated` signal
7. `StatsDisplayWidget` receives signal → updates display
8. Database saves session progress

### Database Schema

**Settings Table** (key-value pairs)
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
-- Examples: theme="nord", font_family="Consolas", font_size="14"
```

**File Stats Table** (per-file statistics)
```sql
CREATE TABLE file_stats (
    file_path TEXT PRIMARY KEY,
    best_wpm REAL DEFAULT 0,
    last_wpm REAL DEFAULT 0,
    completed INTEGER DEFAULT 0
)
```

**Session Progress Table** (resume sessions)
```sql
CREATE TABLE session_progress (
    file_path TEXT PRIMARY KEY,
    cursor_position INTEGER,
    total_characters INTEGER,
    correct_keystrokes INTEGER,
    incorrect_keystrokes INTEGER,
    elapsed_time REAL,
    is_paused INTEGER,
    last_updated TEXT
)
```

**Session History Table** (historical data)
```sql
CREATE TABLE session_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    language TEXT,
    wpm REAL,
    accuracy REAL,
    total_keystrokes INTEGER,
    correct_keystrokes INTEGER,
    incorrect_keystrokes INTEGER,
    duration REAL,
    completed INTEGER,
    recorded_at TEXT
)
```

---

## ⚡ Performance Optimizations

The app has been heavily optimized for fast startup and smooth operation.

### Startup Performance

**Achieved 4.4x faster startup** through these optimizations:

| Optimization | Technique | Time Saved | Impact |
|-------------|-----------|------------|---------|
| **Simplified Folders UI** | Removed complex FolderCardWidget, used simple text list | 2.14s → 0.01s | 99% faster |
| **Lazy Loading** | EditorTab loads on-demand when tab is shown | 0.34s → 0.00s | Deferred to background |
| **Pre-warmed Engine** | Dummy widget initializes Qt stylesheet engine early | 0.28s saved | First addTab() 71% faster |
| **Deferred Theme** | Theme applied after window shown, non-blocking | 0.08s saved | Async loading |
| **Splash Screen** | Immediate visual feedback, parallel loading | N/A | Better UX |

**Startup Timeline:**
```
Cold Start (First boot):   ~1.5-2.5s  (disk I/O bound, OS cache empty)
Warm Start (Second run):   ~0.7-0.9s  (everything cached in RAM)
Splash appears:             ~0.4-0.7s  (user sees immediate feedback)
Main window ready:          ~0.7-0.9s  (fully interactive)
```

### Runtime Optimizations

- **Lazy Tab Initialization**: EditorTab (~0.34s) loads only when accessed
- **Efficient Rendering**: Minimal redraws, only changed widgets update
- **Database Indexing**: File paths indexed for O(1) lookups
- **Signal Throttling**: Stats update every 100ms, not on every keystroke
- **Memory Management**: Proper widget cleanup, no memory leaks

### Code Quality

- **Separation of Concerns**: Business logic independent of GUI
- **Testable Architecture**: Core engine fully unit tested
- **Type Hints**: Full type annotations for better IDE support
- **Comprehensive Tests**: 95%+ coverage on business logic

---

## 📚 Installation

### Prerequisites

- **Python 3.13+** (required for modern type hints and performance)
- **uv** package manager (replaces pip/pip-tools/venv)

### Step-by-Step Installation

#### 1. Install uv (Python Package Manager)

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/Mac (Bash):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Alternative (using pip):**
```bash
pip install uv
```

#### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/dev_type.git
cd dev_type
```

#### 3. Install Dependencies
```bash
uv sync
```

This automatically:
- Creates a virtual environment (`.venv/`)
- Installs Python 3.13 if needed
- Installs PySide6, pytest, and all dependencies
- Locks versions in `uv.lock` for reproducibility

#### 4. Verify Installation
```bash
uv run pytest
```
All tests should pass! ✅

---

## 📖 Usage Guide

### Running the Application

```bash
uv run main.py
```

The app will show a **splash screen** with loading status, then open the main window.

---

## 🧪 Testing

The project has comprehensive test coverage for business logic.

### Running Tests

**Run all tests:**
```bash
uv run pytest
```

**Run with verbose output:**
```bash
uv run pytest -v
```

**Run specific test file:**
```bash
uv run pytest tests/test_typing_engine.py -v
```

**Run with coverage report:**
```bash
uv run pytest --cov=app --cov-report=html tests/
```
Then open `htmlcov/index.html` in a browser to see detailed coverage.

**Run only fast tests (skip slow integration tests):**
```bash
uv run pytest -m "not slow"
```

### Test Structure

```
tests/
├── test_settings_db.py        # Settings CRUD, theme persistence
├── test_stats_db.py           # WPM tracking, session history
├── test_file_scanner.py       # Language detection, file discovery
├── test_typing_engine.py      # Core typing logic, accuracy, WPM
├── test_themes.py             # Color schemes, theme switching
└── test_expanded_settings.py  # Settings expansion and migration
```

### Writing Tests

All business logic is **separated from GUI** for easy testing:

```python
# Example: Testing typing engine (NO GUI required!)
from app.typing_engine import TypingEngine

def test_correct_keystroke():
    engine = TypingEngine("hello")
    result = engine.process_keystroke('h')
    
    assert result.is_correct == True
    assert engine.state.cursor_position == 1
    assert engine.state.correct_keystrokes == 1
    assert engine.state.incorrect_keystrokes == 0
```

### Test Coverage

- **Settings Module**: 100% coverage (CRUD, migrations, defaults)
- **Statistics Module**: 95%+ coverage (WPM, history, progress)
- **File Scanner**: 90%+ coverage (language detection, extensions)
- **Typing Engine**: 100% coverage (keystroke processing, calculations)
- **Themes**: 100% coverage (color schemes, hex validation)

---

## 👨‍💻 Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/dev_type.git
cd dev_type
uv sync

# Run in development mode
uv run main.py
```

### Project Commands

```bash
# Install new dependency
uv add package_name

# Install development dependency (testing, building, etc.)
uv add --dev package_name

# Update all dependencies
uv lock --upgrade

# Format code (if you add ruff/black)
uv run ruff format app/

# Type checking (if you add mypy)
uv run mypy app/

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app tests/
```

### Code Style Guidelines

- **Type Hints**: Use type hints everywhere (`def func(x: int) -> str:`)
- **Docstrings**: Document public methods and classes
- **Separation**: Keep GUI code and business logic separate
- **Testing**: Write tests for business logic (not GUI)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Imports**: Group stdlib, third-party, local imports

### Adding a New Feature

1. **Business Logic First**: Implement in core module (e.g., `typing_engine.py`)
2. **Write Tests**: Add tests in `tests/test_*.py`
3. **GUI Integration**: Add UI components in widget files
4. **Signal/Slot Connections**: Wire up events
5. **Settings Persistence**: Add to `settings.py` if configurable
6. **Documentation**: Update README with new feature

### Debug Mode

Enable debug timing to see performance metrics:

```python
# In app/ui_main.py
DEBUG_STARTUP_TIMING = True  # Shows startup time breakdown
```

Run and see:
```
[STARTUP] QApplication created: 0.097s
[STARTUP] Splash screen shown: 0.425s
[STARTUP] MainWindow created: 0.109s
[STARTUP] TOTAL TIME: 0.880s
```

---

## 📦 Building Executables

Create standalone executables that run without Python installed.

### Prerequisites

Install PyInstaller (development dependency):
```bash
uv add --dev pyinstaller
```

### Windows (.exe)

**Basic Build:**
```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp main.py
```

**Optimized Build (smaller size):**
```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module PIL ^
    main.py
```

**Output:** `dist/DevTypingApp.exe` (~50-80 MB)

**Test it:**
```bash
.\dist\DevTypingApp.exe
```

### Linux

```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp main.py
```

**Output:** `dist/DevTypingApp` (executable)

**Make it executable:**
```bash
chmod +x dist/DevTypingApp
./dist/DevTypingApp
```

### macOS

```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp main.py
```

**Output:** `dist/DevTypingApp.app` (application bundle)

**Run it:**
```bash
open dist/DevTypingApp.app
```

### Advanced PyInstaller Options

```bash
# Custom icon
uv run pyinstaller --onefile --windowed --icon=icon.ico main.py

# Add data files (e.g., demo_files/)
uv run pyinstaller --onefile --windowed \
    --add-data "demo_files:demo_files" \
    main.py

# Reduce size (no console window, strip debug symbols)
uv run pyinstaller --onefile --windowed --strip main.py

# Create installer with Inno Setup (Windows)
# 1. Build executable
# 2. Use Inno Setup Script to create installer
```

### Distribution Options

**Option 1: Single Executable** (Simplest)
- Just share `dist/DevTypingApp.exe`
- User double-clicks to run
- Database created in user's AppData folder

**Option 2: Portable Package** (With Demo Files)
```
DevTypingApp-Portable/
├── DevTypingApp.exe
├── demo_files/
│   ├── demo.py
│   └── demo.js
└── README.txt
```

**Option 3: Installer** (Professional)
- Use **Inno Setup** (Windows) or **NSIS**
- Creates Start Menu shortcuts
- Handles uninstallation
- Can associate file types

### Size Optimization Tips

Reduce executable size from ~200MB to ~50MB:

1. **Exclude unused modules:**
   ```bash
   --exclude-module matplotlib --exclude-module numpy
   ```

2. **Use UPX compression:**
   ```bash
   uv run pyinstaller --onefile --windowed --upx-dir=/path/to/upx main.py
   ```

3. **One-folder mode** (faster startup, larger folder):
   ```bash
   uv run pyinstaller --onedir --windowed main.py
   ```

### Getting Started (Beginner's Tutorial)

1. **Launch the app**: Run `uv run python main.py`
2. **Add Folders**: 
   - Go to the **Folders** tab
   - Click the **+** button
   - Select a folder containing code files (e.g., `demo_files/`)
   - The folder will appear in the list

3. **Browse Languages**: 
   - Switch to the **Languages** tab
   - See files automatically grouped by programming language
   - Each card shows file count and average WPM

4. **Start Typing**: 
   - Double-click a folder in the Folders tab, OR
   - Click a language card in the Languages tab
   - This opens the **Typing** tab

5. **Practice Typing**:
   - Select a file from the file tree on the left
   - The file content appears in the typing area
   - Start typing - the session auto-starts on first keystroke
   - Characters turn **green** for correct, **red** for incorrect
   - Special characters: space→`␣`, enter→`⏎`, tab→4 spaces

### Typing Controls

- **Backspace**: Delete last character
- **Ctrl+Backspace**: Delete word to the left
- **Tab**: Insert 4 spaces
- **Auto-pause**: Session pauses after 7 seconds of inactivity (configurable)
- **Reset button**: Reset cursor to beginning of file

### Statistics

Live stats are displayed at the bottom:
- **WPM** (Words Per Minute): Real-time typing speed
- **Time**: Session duration (MM:SS)
- **Accuracy**: Percentage of correct keystrokes
- **Keystrokes**: Correct/Incorrect/Total counts and percentages
- **Paused indicator**: Shows when session is paused

### Session Persistence

- Sessions are **automatically saved** when you:
  - Switch to a different file
  - Close the application
- **Resume**: Open the same file later to continue where you left off
- Incomplete files are **highlighted** in the file tree
- **Reset**: Use the reset button to start over from the beginning

### File Tree Columns

- **File**: File/folder name
- **Best**: Best WPM ever achieved on this file
- **Last**: Most recent WPM on this file

### Demo Files

Try the included demo files in `demo_files/`:
- `demo.py` - Python examples with functions and classes
- `demo.js` - JavaScript examples with functions and arrays

## Settings

Access comprehensive settings from the **Settings** tab:

### General Settings
- **Delete confirmation dialogs**: Toggle confirmation when removing folders
- **Show typed character**: Display what you typed (not expected character) when incorrect

### Theme Settings ✨
Switch themes instantly with no restart required!

- **Theme**: Choose between **dark** and **light** mode
- **Dark schemes**: Three beautiful options
  - **Nord** (Default): Arctic, north-bluish palette - professional and calming
  - **Catppuccin**: Soothing pastel theme - cozy and comfortable
  - **Dracula**: Vibrant dark theme - bold and dramatic
  
**Theme colors apply instantly** to:
- All UI elements (buttons, tabs, lists, trees, inputs)
- Typing area text colors
- Scroll bars, borders, and accents
- Message dialogs

### Color Customization
- **Untyped text color**: Color for characters not yet typed (default: gray)
- **Correct text color**: Color for correctly typed characters (default: green)
- **Incorrect text color**: Color for incorrectly typed characters (default: red)
- **Paused files highlight**: Color for incomplete session files (default: orange)
- **Cursor color**: Color of the text cursor (default: white)
- Each color has a **Reset** button to restore defaults

### Cursor Settings
- **Type**: Blinking or static cursor
- **Style**: Block, underscore, or I-beam cursor

### Font Settings
- **Family**: Choose from popular monospace fonts (Consolas, Fira Code, JetBrains Mono, etc.)
- **Size**: Font size from 8 to 32 pixels
- **Ligatures**: Enable or disable font ligatures

### Typing Settings
- **Space character**: Choose how spaces are displayed: `␣`, `·`, ` ` (normal space), or custom character
- **Auto-pause delay**: Seconds of inactivity before session pauses (default: 7 seconds)

### Backup & Restore
- **Export Settings**: Save all settings to a JSON file
- **Import Settings**: Load settings from a JSON file
- **Export Data**: Save typing statistics and progress to JSON
- **Import Data**: Load typing statistics and progress from JSON

All settings are persisted in an SQLite database at:
- Windows: `%APPDATA%\dev_typing_app\data.db`
- Linux/Mac: `~/.local/share/dev_typing_app/data.db`

## Testing

The project has comprehensive test coverage for core logic:

- Settings management (SQLite operations)
- Statistics tracking (WPM, accuracy, sessions)
- File scanning and language detection
- Typing engine (keystroke processing, accuracy, WPM calculation)

All business logic is tested independently of the GUI.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/dev_type/issues)
2. If not, create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your OS and Python version

### Suggesting Features

1. Check existing [Issues](https://github.com/yourusername/dev_type/issues) and [Discussions](https://github.com/yourusername/dev_type/discussions)
2. Create a new issue with "Feature Request" label
3. Describe the feature and its benefits
4. Provide mockups or examples if possible

### Contributing Code

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/yourusername/dev_type.git
   cd dev_type
   ```
3. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. **Make your changes:**
   - Write code following project style
   - Add tests for new functionality
   - Update documentation
5. **Test your changes:**
   ```bash
   uv run pytest
   ```
6. **Commit with clear messages:**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
7. **Push to your fork:**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Create a Pull Request** on GitHub

### Development Guidelines

- **Code Style**: Follow PEP 8, use type hints
- **Testing**: Write tests for business logic (95%+ coverage target)
- **Documentation**: Update README and docstrings
- **Commit Messages**: Use [Conventional Commits](https://www.conventionalcommits.org/)
  - `feat:` new feature
  - `fix:` bug fix
  - `docs:` documentation
  - `perf:` performance improvement
  - `refactor:` code refactoring
  - `test:` adding tests

### Good First Issues

Look for issues labeled **"good first issue"** - these are beginner-friendly!

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

✅ **Permissions:**
- Commercial use
- Modification
- Distribution
- Private use

❌ **Limitations:**
- Liability
- Warranty

ℹ️ **Conditions:**
- License and copyright notice must be included

---

## 🗺️ Roadmap

### ✅ Completed (v0.1.0)
- [x] Core typing engine with WPM and accuracy
- [x] Multi-folder management
- [x] Language detection and grouping
- [x] Session persistence and resume
- [x] 4 themes (Nord, Catppuccin, Dracula, Light)
- [x] Comprehensive statistics and history
- [x] Full customization (colors, fonts, cursor)
- [x] Export/import settings and data
- [x] Performance optimizations (4.4x faster startup)
- [x] Splash screen with loading status
- [x] Keystroke display with percentages
- [x] Comprehensive testing suite

### 🚧 In Progress (v0.2.0)
- [ ] Language icons/logos
- [ ] Code syntax highlighting in typing area
- [ ] Dark theme for dialogs (currently system default)
- [ ] Progress bar on splash screen

### 📋 Planned (v0.3.0+)
- [ ] Speed test mode (1-minute, 5-minute challenges)
- [ ] Daily goals and streaks
- [ ] Achievements and badges
- [ ] Leaderboards (optional online feature)
- [ ] Code snippet library (practice specific patterns)
- [ ] Multi-language UI (i18n)
- [ ] Plugin system for custom themes
- [ ] Cloud sync (optional)

### 💡 Ideas (Community Suggestions)
- [ ] Multiplayer/competitive typing races
- [ ] Practice mode with guided tutorials
- [ ] Smart practice (focus on weak areas)
- [ ] Integration with GitHub repos
- [ ] VS Code extension
- [ ] Mobile companion app

**Have an idea?** [Open a discussion](https://github.com/yourusername/dev_type/discussions/new?category=ideas)!

---

## 🙏 Acknowledgments

- **Qt Project**: For the excellent Qt framework
- **PySide6 Team**: For Python bindings to Qt
- **Nord Theme**: Arctic, north-bluish color palette
- **Catppuccin**: Soothing pastel theme
- **Dracula**: Dark theme for many applications
- **uv**: Blazing-fast Python package manager
- **Contributors**: Everyone who has contributed to this project

---

## 📞 Support

- 📖 **Documentation**: Read this README
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/dev_type/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/dev_type/issues)
- 📧 **Email**: your.email@example.com (for private inquiries)

---

## 🌟 Show Your Support

If you find this project useful, please consider:

- ⭐ **Star** the repository
- 🐛 **Report bugs** and suggest features
- 📢 **Share** with fellow developers
- 💻 **Contribute** code or documentation

---

<div align="center">

**Made with ❤️ by developers, for developers**

[⬆ Back to Top](#️-dev-typing-app)

</div>