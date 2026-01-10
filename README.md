# ⌨️ Dev Typing App

A modern typing practice application designed specifically for developers. Practice your typing skills by typing real code from your projects, with features tailored for programmers.

## ✨ Features

- **📁 Code Folder Integration**: Add folders containing your code projects and practice typing on real code files
- **🔍 Language Detection**: Automatically scans and categorizes files by programming language
- **⚡ Typing Practice**: Interactive typing interface with real-time feedback
- **🎨 Themes & Customization**: Multiple dark/light themes with color schemes (Nord, Catppuccin, Dracula)
- **🔊 Sound Effects**: Optional typing sounds with customizable profiles
- **📊 Statistics Tracking**: Comprehensive stats including WPM, accuracy, and progress tracking
- **📜 Session History**: Review past typing sessions and performance trends
- **👻 Ghost Replays**: Compare your current typing against previous best performances
- **💾 Portable Data**: Configurable data directory for stats, ghosts, and custom sounds
- **⚙️ Settings**: Extensive customization options for fonts, cursors, colors, and typing behavior

## 🚀 Installation and Running

### Prerequisites

- Python 3.13 or higher
- Git

### Option 1: Using uv (⭐ Recommended)

uv is a fast Python package installer and resolver that makes dependency management easier.

**Don't have uv installed?** 📥 Follow the installation guide here: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mehad605/dev_type.git
   cd dev_type
   ```

2. **Sync dependencies:**
   ```bash
   uv sync
   ```

3. **Run the application:**
   ```bash
   uv run main.py
   ```

### Option 2: Using pip

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mehad605/dev_type.git
   cd dev_type
   ```

2. **Create a virtual environment (recommended):**
   
   **Windows (PowerShell):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
   
   **Linux/macOS:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install .
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## 📦 Building Standalone Executable

To create a standalone executable that doesn't require running `uv run` or `python` commands every time, you can build a portable executable.

### Prerequisites for Building

Before building, ensure you have:

1. **Python 3.13 or higher** installed
2. **PyInstaller** installed:
   ```bash
   # If using uv
   uv pip install pyinstaller
   
   # If using regular pip
   pip install pyinstaller
   ```
3. **All project dependencies** installed (via `uv sync` or `pip install .`)

### 🪟 Building on Windows

The project includes a convenient build script for Windows:

```bash
build.bat
```

Or manually using the build script:

```bash
# Using uv (recommended)
uv run python build.py --windows --clean

# Using regular python
python build.py --windows --clean
```

This will:
- Create a single-file executable `dev_type.exe`
- Bundle all Python dependencies and assets
- Include themes, sounds, and default configurations
- Place the executable in the `dist/` directory

### 🐧 Building on Linux

The project includes a shell script for building on Linux and packaging as an AppImage:

```bash
chmod +x build.sh
./build.sh
```

Or manually using the build script:

```bash
# Package as AppImage (requires appimagetool in PATH)
uv run python build.py --linux --appimage --clean

# Build standalone binary only
uv run python build.py --linux --clean
```

This will create an `AppDir` and a `dev_type.AppImage` in the `dist/` directory. If `appimagetool` is not in your PATH, it will still create the `AppDir` structure which you can manually package.

### What the Build Does

- Creates a standalone executable using PyInstaller
- Bundles all Python dependencies and required libraries
- Includes application assets (icons, sounds, etc.)
- Produces a portable application that runs without Python installation
- On first run, automatically creates a `Dev_Type_Data/` folder for storing:
  - User settings
  - Typing statistics
  - Session history
  - Custom sounds and ghosts

### After Building

1. Find your executable in the `dist/` folder
2. Run `dev_type.exe` (Windows) - no Python required! 🎉
3. The data folder will be created automatically next to the executable
4. To update: replace the executable, keep your data folder to preserve settings and stats

## 🎯 Usage

1. **Add Code Folders**: Use the "Folders" tab to add directories containing code you want to practice with
2. **Select Language**: Go to the "Languages" tab to see detected programming languages and file counts
3. **Start Typing**: Click on a language or folder to begin a typing session
4. **Customize**: Adjust settings in the "Settings" tab for themes, sounds, fonts, and behavior
5. **Track Progress**: View your statistics and history in the respective tabs

## 🔧 Configuration

The app stores settings, statistics, and custom data in a configurable data directory. By default, this is next to the executable, but you can change it in Settings > Data Directory.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) - see the [LICENSE](LICENSE) file for details.

**In short:** 
- **Personal Use**: You can use this app for any personal use.
- **Non-Commercial**: You cannot make use of it for financial gain.
- **ShareAlike**: Any and all derivatives of this project must also be made open-source and must have the same or more open licensing.