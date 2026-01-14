# ⌨️ Dev Type

A modern, high-performance typing practice application designed specifically for developers. Practice your typing skills by typing real code from your projects, with features tailored for programmers.

---

## 📥 Downloads

If you just want to use the app, you can download the latest pre-built binaries from the GitHub Releases page:

- **Windows**: `dev_type_vX.Y.Z.exe` (Portable executable)
*   **Linux**: `dev_type_vX.Y.Z.deb` (Debian/Ubuntu package)

👉 **[Download Latest Release](https://github.com/mehad605/dev_type/releases/latest)**

---

## 🎬 Demo

<div align="center">
  <video src="https://github.com/user-attachments/assets/ef18ab02-c152-4711-a8ab-fa79f8841734" width="70%"> </video>
</div>

---

## ✨ Features

- **📁 Code Folder Integration**: Add folders containing your code projects and practice typing on real code files.
- **🔍 Language Detection**: Automatically scans and categorizes files by programming language.
- **⚡ Typing Practice**: High-performance interactive typing interface with real-time syntax highlighting feedback.
- **📊 Statistics Tracking**: Comprehensive stats including WPM, accuracy, and detailed progress charts.
- **👻 Ghost Replays**: Race against your previous best performances.
- **🔊 Sound Effects**: Mechanical keyboard sounds with customizable profiles.
- **🎨 Color Schemes**: Beautiful dark themes including Nord, Catppuccin, and Dracula.
- **💾 Portable Data**: Keep your stats and settings in a local folder or move them between machines.

---

## 📸 Screenshots

| Typing Practice | Folder Explorer |
| :---: | :---: |
| ![Typing](assets/Screenshots/typing_tab.png) | ![Folders](assets/Screenshots/folder_tab.png) |

| Session History | Language Stats |
| :---: | :---: |
| ![History](assets/Screenshots/history_tab.png) | ![Languages](assets/Screenshots/language_tab.png) |

| Performance Stats | Extensive Settings |
| :---: | :---: |
| ![Stats](assets/Screenshots/stats_tab.png) | ![Settings](assets/Screenshots/settings_tab.png) |

---

## 🚀 Development Setup (Run from Source)

If you want to run the latest development version:

### Prerequisites
- **Python 3.13** or higher
- **Git**

### Using uv (⭐ Recommended)
uv is a blazing fast Python package manager. 
*Don't have uv?* [Install it here](https://docs.astral.sh/uv/getting-started/installation/).

1. **Clone & Enter:**
   ```bash
   git clone https://github.com/mehad605/dev_type.git
   cd dev_type
   ```
2. **Setup & Run:**
   ```bash
   uv sync
   uv run main.py
   ```

### Using standard pip
1. **Clone & Enter:**
   ```bash
   git clone https://github.com/mehad605/dev_type.git
   cd dev_type
   ```
2. **Create Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. **Install & Run:**
   ```bash
   pip install .
   python main.py
   ```

---

## 📦 Building from Source

You can generate your own standalone binaries using the included build system.

### 🪟 Windows (.exe)
Double-click `build.bat` or run:
```bash
uv run python build.py --windows --clean
```
The output will be a portable executable in the `dist/` folder named `dev_type_vX.Y.Z.exe`.

### 🐧 Linux (.deb)
Run the build script:
```bash
chmod +x build.sh
./build.sh
```
Or manually:
```bash
uv run python build.py --linux --clean
```
This will generate a Debian package `dev_type_vX.Y.Z.deb` in the `dist/` folder, which can be installed via `sudo apt install ./dist/dev_type_vX.Y.Z.deb`.

---

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

- **Non-Commercial**: You cannot use this for financial gain.
- **ShareAlike**: Derivatives must use the same open license.
- **Attribution**: You must give appropriate credit.

[Full License Details](LICENSE)
