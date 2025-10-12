# Dev Typing App

A Python-based typing practice application specifically designed for developers to improve their typing speed on real code files.

## Features

- **Folder Management**: Add multiple folders containing your code files
- **Language Detection**: Automatically groups files by programming language
- **File Tree View**: Browse files with best/last WPM statistics
- **Typing Practice**: Character-by-character typing validation with color coding
- **Statistics Tracking**: WPM, accuracy, and keystroke metrics
- **Session Persistence**: Resume incomplete typing sessions
- **Dynamic Themes** ✨: 3 dark schemes (Nord, Catppuccin, Dracula) + light mode - switch instantly!
- **Full Customization**: Colors, fonts, cursor styles, and more
- **Import/Export**: Backup and restore settings and data
- **Offline**: Works completely offline once set up

## Quick Start

```bash
# 1. Install uv (if not already installed)
# Windows: https://github.com/astral-sh/uv#installation
# Linux/Mac: curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and setup
git clone <repository-url>
cd dev_type
uv sync

# 3. Run the app
uv run python main.py

# 4. Try it out!
# - Add the demo_files/ folder
# - Go to Languages tab
# - Click on Python or JavaScript
# - Select a file and start typing!
```

## Tech Stack

- **Python 3.13+**
- **PySide6** (Qt6) - Cross-platform GUI
- **SQLite** - Local database for settings and statistics
- **pytest** - Testing framework
- **uv** - Fast Python package manager

## Project Structure

```
dev_type/
├── app/
│   ├── __init__.py
│   ├── settings.py          # SQLite-backed settings management
│   ├── stats_db.py           # Typing statistics database
│   ├── file_scanner.py       # Language detection and file scanning
│   ├── typing_engine.py      # Core typing logic (no GUI dependencies)
│   ├── themes.py             # Theme system with color schemes
│   ├── typing_area.py        # Typing area widget with syntax highlighting
│   ├── stats_display.py      # Live stats display widget
│   ├── file_tree.py          # File tree widget
│   ├── editor_tab.py         # Editor/typing tab integration
│   ├── languages_tab.py      # Languages tab widget
│   └── ui_main.py            # Main window and UI
├── tests/
│   ├── test_settings_db.py
│   ├── test_stats_db.py
│   ├── test_file_scanner.py
│   ├── test_typing_engine.py
│   ├── test_themes.py
│   └── test_expanded_settings.py
├── main.py                   # Application entry point
├── pyproject.toml            # Project configuration (managed by uv)
└── README.md

```

## Development Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dev_type
```

2. Install dependencies with uv:
```bash
uv sync
```

This will create a virtual environment and install all dependencies from `pyproject.toml`.

### Running the Application

```bash
uv run python main.py
```

Or simply:
```bash
uv run main.py
```

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run specific test file:
```bash
uv run pytest tests/test_typing_engine.py -v
```

Run with coverage:
```bash
uv run pytest --cov=app tests/
```

### Adding Dependencies

To add a new dependency:
```bash
uv add package_name
```

To add a development dependency:
```bash
uv add --dev package_name
```

## Building Executables

### Windows (.exe)

Install PyInstaller:
```bash
uv add --dev pyinstaller
```

Build the executable:
```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp main.py
```

The executable will be in `dist/DevTypingApp.exe`.

### Linux

Install PyInstaller:
```bash
uv add --dev pyinstaller
```

Build the executable:
```bash
uv run pyinstaller --onefile --windowed --name DevTypingApp main.py
```

The executable will be in `dist/DevTypingApp`.

### Creating Portable Packages

For a portable installation (no install required):

1. Build the executable as above
2. Copy the `dist/` folder contents
3. Users can run the executable directly

## Usage

### Getting Started

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Submit a pull request

## License

[Add your license here]

## TODO / Roadmap

- [ ] Typing area widget implementation
- [ ] Stats display widget
- [ ] Complete editor tab integration
- [ ] Theme/color scheme application
- [ ] Language icon downloading
- [ ] Export/import settings and data
- [ ] Additional typing modes (speed tests, challenges)
- [ ] Multiplayer/competitive modes