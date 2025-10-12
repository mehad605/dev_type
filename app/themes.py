"""Theme management with Nord, Catppuccin, and Dracula color schemes.

This module provides theme definitions and application logic for the typing app.
Themes include complete color schemes for UI elements, text editor, and all widgets.
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ColorScheme:
    """Color scheme definition for a theme."""
    # Background colors
    bg_primary: str  # Main background
    bg_secondary: str  # Secondary background (sidebars, etc.)
    bg_tertiary: str  # Tertiary background (hover, selection)
    
    # Text colors
    text_primary: str  # Main text
    text_secondary: str  # Secondary text (labels, etc.)
    text_disabled: str  # Disabled text
    
    # Typing colors
    text_untyped: str  # Not yet typed
    text_correct: str  # Correctly typed
    text_incorrect: str  # Incorrectly typed
    text_paused: str  # Paused file highlight
    cursor_color: str  # Cursor color
    
    # UI colors
    border_color: str  # Widget borders
    accent_color: str  # Accent/selection color
    button_bg: str  # Button background
    button_hover: str  # Button hover
    
    # Status colors
    success_color: str  # Success messages
    warning_color: str  # Warning messages
    error_color: str  # Error messages
    info_color: str  # Info messages


# Nord Theme (Arctic, north-bluish color palette)
NORD_DARK = ColorScheme(
    # Backgrounds - Nord polar night colors
    bg_primary="#2e3440",  # nord0 - darkest
    bg_secondary="#3b4252",  # nord1 - dark
    bg_tertiary="#434c5e",  # nord2 - medium dark
    
    # Text - Nord snow storm colors
    text_primary="#eceff4",  # nord6 - bright white
    text_secondary="#d8dee9",  # nord4 - medium white
    text_disabled="#4c566a",  # nord3 - gray
    
    # Typing colors
    text_untyped="#616e88",  # Muted nord3
    text_correct="#a3be8c",  # nord14 - green
    text_incorrect="#bf616a",  # nord11 - red
    text_paused="#ebcb8b",  # nord13 - yellow
    cursor_color="#88c0d0",  # nord8 - bright cyan
    
    # UI colors
    border_color="#4c566a",  # nord3
    accent_color="#5e81ac",  # nord10 - blue
    button_bg="#434c5e",  # nord2
    button_hover="#4c566a",  # nord3
    
    # Status colors
    success_color="#a3be8c",  # nord14 - green
    warning_color="#ebcb8b",  # nord13 - yellow
    error_color="#bf616a",  # nord11 - red
    info_color="#81a1c1",  # nord9 - light blue
)


# Catppuccin Mocha (Soothing pastel theme)
CATPPUCCIN_DARK = ColorScheme(
    # Backgrounds - Catppuccin base colors
    bg_primary="#1e1e2e",  # base
    bg_secondary="#181825",  # mantle
    bg_tertiary="#313244",  # surface0
    
    # Text - Catppuccin text colors
    text_primary="#cdd6f4",  # text
    text_secondary="#bac2de",  # subtext1
    text_disabled="#585b70",  # surface2
    
    # Typing colors
    text_untyped="#6c7086",  # overlay0
    text_correct="#a6e3a1",  # green
    text_incorrect="#f38ba8",  # red
    text_paused="#f9e2af",  # yellow
    cursor_color="#89dceb",  # sky
    
    # UI colors
    border_color="#45475a",  # surface1
    accent_color="#89b4fa",  # blue
    button_bg="#313244",  # surface0
    button_hover="#45475a",  # surface1
    
    # Status colors
    success_color="#a6e3a1",  # green
    warning_color="#f9e2af",  # yellow
    error_color="#f38ba8",  # red
    info_color="#74c7ec",  # sapphire
)


# Dracula Theme (Dark theme inspired by vampires)
DRACULA_DARK = ColorScheme(
    # Backgrounds - Dracula base colors
    bg_primary="#282a36",  # background
    bg_secondary="#21222c",  # darker bg
    bg_tertiary="#44475a",  # current line
    
    # Text - Dracula text colors
    text_primary="#f8f8f2",  # foreground
    text_secondary="#e6e6e6",  # lighter
    text_disabled="#6272a4",  # comment
    
    # Typing colors
    text_untyped="#6272a4",  # comment
    text_correct="#50fa7b",  # green
    text_incorrect="#ff5555",  # red
    text_paused="#f1fa8c",  # yellow
    cursor_color="#8be9fd",  # cyan
    
    # UI colors
    border_color="#44475a",  # current line
    accent_color="#bd93f9",  # purple
    button_bg="#44475a",  # current line
    button_hover="#6272a4",  # comment
    
    # Status colors
    success_color="#50fa7b",  # green
    warning_color="#f1fa8c",  # yellow
    error_color="#ff5555",  # red
    info_color="#8be9fd",  # cyan
)


# Light theme (for light mode)
LIGHT_THEME = ColorScheme(
    # Backgrounds
    bg_primary="#ffffff",
    bg_secondary="#f5f5f5",
    bg_tertiary="#e0e0e0",
    
    # Text
    text_primary="#212121",
    text_secondary="#424242",
    text_disabled="#9e9e9e",
    
    # Typing colors
    text_untyped="#757575",
    text_correct="#2e7d32",  # Darker green for light bg
    text_incorrect="#c62828",  # Darker red for light bg
    text_paused="#f57c00",  # Darker orange for light bg
    cursor_color="#1976d2",  # Blue cursor
    
    # UI colors
    border_color="#bdbdbd",
    accent_color="#1976d2",  # Blue accent
    button_bg="#e0e0e0",
    button_hover="#d0d0d0",
    
    # Status colors
    success_color="#2e7d32",
    warning_color="#f57c00",
    error_color="#c62828",
    info_color="#0288d1",
)


# Theme registry
THEMES: Dict[str, Dict[str, ColorScheme]] = {
    "dark": {
        "nord": NORD_DARK,
        "catppuccin": CATPPUCCIN_DARK,
        "dracula": DRACULA_DARK,
    },
    "light": {
        "default": LIGHT_THEME,
    }
}


def get_color_scheme(theme: str = "dark", scheme: str = "nord") -> ColorScheme:
    """Get a color scheme by theme and scheme name.
    
    Args:
        theme: Theme type ("dark" or "light")
        scheme: Scheme name ("nord", "catppuccin", "dracula") for dark mode
        
    Returns:
        ColorScheme object with all colors
    """
    if theme == "light":
        return LIGHT_THEME
    
    # Default to nord if scheme not found
    return THEMES["dark"].get(scheme, NORD_DARK)


def generate_app_stylesheet(scheme: ColorScheme) -> str:
    """Generate complete Qt stylesheet for the application.
    
    Args:
        scheme: ColorScheme to use
        
    Returns:
        Complete Qt stylesheet string
    """
    return f"""
    /* Main Application */
    QMainWindow, QWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
    }}
    
    /* Tabs */
    QTabWidget::pane {{
        border: 1px solid {scheme.border_color};
        background-color: {scheme.bg_primary};
    }}
    
    QTabBar::tab {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_secondary};
        padding: 8px 16px;
        border: 1px solid {scheme.border_color};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border-bottom: 2px solid {scheme.accent_color};
    }}
    
    QTabBar::tab:hover {{
        background-color: {scheme.bg_tertiary};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 6px 12px;
        border-radius: 4px;
    }}
    
    QPushButton:hover {{
        background-color: {scheme.button_hover};
        border-color: {scheme.accent_color};
    }}
    
    QPushButton:pressed {{
        background-color: {scheme.bg_tertiary};
    }}
    
    QPushButton:disabled {{
        color: {scheme.text_disabled};
        background-color: {scheme.bg_secondary};
    }}
    
    /* Text Edits */
    QTextEdit, QPlainTextEdit {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
    }}
    
    /* List Widgets */
    QListWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
    }}
    
    QListWidget::item:hover {{
        background-color: {scheme.bg_tertiary};
    }}
    
    /* Tree Widgets */
    QTreeWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
    }}
    
    QTreeWidget::item:hover {{
        background-color: {scheme.bg_tertiary};
    }}
    
    /* Combo Boxes */
    QComboBox {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    
    QComboBox:hover {{
        border-color: {scheme.accent_color};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        selection-background-color: {scheme.accent_color};
    }}
    
    /* Spin Boxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 4px;
        border-radius: 4px;
    }}
    
    QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {scheme.accent_color};
    }}
    
    /* Check Boxes */
    QCheckBox {{
        color: {scheme.text_primary};
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {scheme.border_color};
        border-radius: 3px;
        background-color: {scheme.bg_secondary};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {scheme.accent_color};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {scheme.accent_color};
        border-color: {scheme.accent_color};
    }}
    
    /* Group Boxes */
    QGroupBox {{
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 8px;
    }}
    
    QGroupBox::title {{
        color: {scheme.accent_color};
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    
    /* Labels */
    QLabel {{
        color: {scheme.text_primary};
    }}
    
    /* Scroll Bars */
    QScrollBar:vertical {{
        background-color: {scheme.bg_secondary};
        width: 12px;
        border: none;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {scheme.border_color};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {scheme.accent_color};
    }}
    
    QScrollBar:horizontal {{
        background-color: {scheme.bg_secondary};
        height: 12px;
        border: none;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {scheme.border_color};
        border-radius: 6px;
        min-width: 20px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {scheme.accent_color};
    }}
    
    QScrollBar::add-line, QScrollBar::sub-line {{
        border: none;
        background: none;
    }}
    
    /* Scroll Area */
    QScrollArea {{
        background-color: {scheme.bg_primary};
        border: none;
    }}
    
    /* Message Box */
    QMessageBox {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
    }}
    
    QMessageBox QLabel {{
        color: {scheme.text_primary};
    }}
    
    QMessageBox QPushButton {{
        min-width: 80px;
    }}
    
    /* Splitter */
    QSplitter::handle {{
        background-color: {scheme.border_color};
    }}
    
    QSplitter::handle:hover {{
        background-color: {scheme.accent_color};
    }}
    
    /* Menu Bar */
    QMenuBar {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_primary};
    }}
    
    QMenuBar::item:selected {{
        background-color: {scheme.accent_color};
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_secondary};
    }}
    """


def apply_theme_to_app(app, scheme: ColorScheme):
    """Apply color scheme to entire QApplication.
    
    Args:
        app: QApplication instance
        scheme: ColorScheme to apply
    """
    stylesheet = generate_app_stylesheet(scheme)
    app.setStyleSheet(stylesheet)
