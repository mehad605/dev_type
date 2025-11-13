@echo off
REM Windows build script for dev_type
REM Double-click this file to build the portable executable

echo ========================================
echo   Dev Type - Windows Build
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Check if uv is available (preferred)
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using uv to run build script...
    uv run python build.py --windows --clean
) else (
    echo Using python to run build script...
    python build.py --windows --clean
)

echo.
echo ========================================
echo   Clearing Windows Icon Cache
echo ========================================
echo.
echo This ensures the latest icon is displayed...
echo (Developer-only step - end users don't need this)
echo.

REM Kill Explorer to release icon cache
taskkill /IM explorer.exe /F >nul 2>&1

REM Delete icon cache files
DEL /Q "%localappdata%\IconCache.db" >nul 2>&1
DEL /Q "%localappdata%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1

REM Restart Explorer
start explorer.exe

echo Icon cache cleared successfully!

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Your executable is in the dist\ folder
echo.

pause
