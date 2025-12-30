"""Theme management with Nord, Catppuccin, and Dracula color schemes.

This module provides theme definitions and application logic for the typing app.
Themes include complete color schemes for UI elements, text editor, and all widgets.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Cache for generated stylesheets to avoid regeneration
_stylesheet_cache: Dict[str, str] = {}


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


# Cyberpunk (High contrast neon)
CYBERPUNK_DARK = ColorScheme(
    # Backgrounds
    bg_primary="#0b0c15",  # Deep dark blue/black
    bg_secondary="#161822",  # Slightly lighter
    bg_tertiary="#2a2d3e",  # Selection bg
    
    # Text
    text_primary="#00ff9f",  # Neon Green
    text_secondary="#00b8ff",  # Neon Blue
    text_disabled="#565869",
    
    # Typing colors
    text_untyped="#565869",
    text_correct="#fcee0a",  # Neon Yellow
    text_incorrect="#ff003c",  # Neon Red
    text_paused="#00b8ff",  # Neon Blue
    cursor_color="#ff003c",  # Neon Red
    
    # UI colors
    border_color="#2a2d3e",
    accent_color="#ff003c",  # Neon Red
    button_bg="#161822",
    button_hover="#2a2d3e",
    
    # Status colors
    success_color="#00ff9f",
    warning_color="#fcee0a",
    error_color="#ff003c",
    info_color="#00b8ff",
)


# Monokai Pro (Professional dark theme)
MONOKAI_PRO = ColorScheme(
    # Backgrounds
    bg_primary="#2D2A2E",
    bg_secondary="#403E41",
    bg_tertiary="#5B595C",
    
    # Text
    text_primary="#FCFCFA",
    text_secondary="#939293",
    text_disabled="#727072",
    
    # Typing colors
    text_untyped="#727072",
    text_correct="#A9DC76",  # Green
    text_incorrect="#FF6188",  # Red
    text_paused="#FFD866",  # Yellow
    cursor_color="#78DCE8",  # Blue
    
    # UI colors
    border_color="#5B595C",
    accent_color="#FFD866",  # Yellow accent
    button_bg="#403E41",
    button_hover="#5B595C",
    
    # Status colors
    success_color="#A9DC76",
    warning_color="#FFD866",
    error_color="#FF6188",
    info_color="#78DCE8",
)


# Gruvbox Dark (Retro warm theme)
GRUVBOX_DARK = ColorScheme(
    # Backgrounds
    bg_primary="#282828",
    bg_secondary="#3c3836",
    bg_tertiary="#504945",
    
    # Text
    text_primary="#ebdbb2",
    text_secondary="#a89984",
    text_disabled="#928374",
    
    # Typing colors
    text_untyped="#928374",
    text_correct="#b8bb26",  # Green
    text_incorrect="#fb4934",  # Red
    text_paused="#fabd2f",  # Yellow
    cursor_color="#fe8019",  # Orange
    
    # UI colors
    border_color="#504945",
    accent_color="#d3869b",  # Purple
    button_bg="#3c3836",
    button_hover="#504945",
    
    # Status colors
    success_color="#b8bb26",
    warning_color="#fabd2f",
    error_color="#fb4934",
    info_color="#83a598",
)


# Solarized Dark (Precision colors)
SOLARIZED_DARK = ColorScheme(
    # Backgrounds
    bg_primary="#002b36",
    bg_secondary="#073642",
    bg_tertiary="#586e75",
    
    # Text
    text_primary="#839496",
    text_secondary="#586e75",
    text_disabled="#657b83",
    
    # Typing colors
    text_untyped="#657b83",
    text_correct="#859900",  # Green
    text_incorrect="#dc322f",  # Red
    text_paused="#b58900",  # Yellow
    cursor_color="#268bd2",  # Blue
    
    # UI colors
    border_color="#586e75",
    accent_color="#268bd2",  # Blue
    button_bg="#073642",
    button_hover="#586e75",
    
    # Status colors
    success_color="#859900",
    warning_color="#b58900",
    error_color="#dc322f",
    info_color="#268bd2",
)


# Rose Pine Dawn (Soft warm light)
ROSE_PINE_DAWN = ColorScheme(
    # Backgrounds
    bg_primary="#faf4ed",
    bg_secondary="#fffaf3",
    bg_tertiary="#f2e9e1",
    
    # Text
    text_primary="#575279",
    text_secondary="#797593",
    text_disabled="#9893a5",
    
    # Typing colors
    text_untyped="#9893a5",
    text_correct="#286983",  # Pine
    text_incorrect="#b4637a",  # Love
    text_paused="#ea9d34",  # Gold
    cursor_color="#56949f",  # Foam
    
    # UI colors
    border_color="#dfdad9",
    accent_color="#d7827e",  # Rose
    button_bg="#fffaf3",
    button_hover="#f2e9e1",
    
    # Status colors
    success_color="#286983",
    warning_color="#ea9d34",
    error_color="#b4637a",
    info_color="#56949f",
)


# Solarized Light (Precision light)
SOLARIZED_LIGHT = ColorScheme(
    # Backgrounds
    bg_primary="#fdf6e3",
    bg_secondary="#eee8d5",
    bg_tertiary="#e0dcc7",
    
    # Text
    text_primary="#657b83",
    text_secondary="#93a1a1",
    text_disabled="#a1a1a1",
    
    # Typing colors
    text_untyped="#93a1a1",
    text_correct="#859900",  # Green
    text_incorrect="#dc322f",  # Red
    text_paused="#b58900",  # Yellow
    cursor_color="#268bd2",  # Blue
    
    # UI colors
    border_color="#d3d0c8",
    accent_color="#268bd2",  # Blue
    button_bg="#eee8d5",
    button_hover="#e0dcc7",
    
    # Status colors
    success_color="#859900",
    warning_color="#b58900",
    error_color="#dc322f",
    info_color="#268bd2",
)


# Catppuccin Latte (Vibrant light)
CATPPUCCIN_LATTE = ColorScheme(
    # Backgrounds
    bg_primary="#eff1f5",
    bg_secondary="#e6e9ef",
    bg_tertiary="#bcc0cc",
    
    # Text
    text_primary="#4c4f69",
    text_secondary="#6c6f85",
    text_disabled="#9ca0b0",
    
    # Typing colors
    text_untyped="#9ca0b0",
    text_correct="#40a02b",  # Green
    text_incorrect="#d20f39",  # Red
    text_paused="#df8e1d",  # Yellow
    cursor_color="#ea76cb",  # Pink
    
    # UI colors
    border_color="#ccd0da",
    accent_color="#8839ef",  # Mauve
    button_bg="#e6e9ef",
    button_hover="#bcc0cc",
    
    # Status colors
    success_color="#40a02b",
    warning_color="#df8e1d",
    error_color="#d20f39",
    info_color="#1e66f5",
)


# Theme registry
THEMES: Dict[str, Dict[str, ColorScheme]] = {
    "dark": {
        "nord": NORD_DARK,
        "catppuccin": CATPPUCCIN_DARK,
        "dracula": DRACULA_DARK,
        "cyberpunk": CYBERPUNK_DARK,
        "monokai_pro": MONOKAI_PRO,
        "gruvbox": GRUVBOX_DARK,
        "solarized_dark": SOLARIZED_DARK,
    },
    "light": {
        "default": LIGHT_THEME,
        "rose_pine_dawn": ROSE_PINE_DAWN,
        "solarized_light": SOLARIZED_LIGHT,
        "catppuccin_latte": CATPPUCCIN_LATTE,
    }
}


def get_color_scheme(theme: str = "dark", scheme: str = "nord") -> ColorScheme:
    """Get a color scheme by theme and scheme name.
    
    Args:
        theme: Theme type ("dark" or "light")
        scheme: Scheme name ("nord", "catppuccin", "dracula", etc.)
        
    Returns:
        ColorScheme object with all colors
    """
    if theme == "light":
        return THEMES["light"].get(scheme, LIGHT_THEME)
    
    # Default to nord if scheme not found
    return THEMES["dark"].get(scheme, NORD_DARK)


def generate_app_stylesheet(scheme: ColorScheme) -> str:
    """Generate complete Qt stylesheet for the application.
    
    Uses caching to avoid regenerating the same stylesheet multiple times.
    
    Args:
        scheme: ColorScheme to use
        
    Returns:
        Complete Qt stylesheet string
    """
    # Create cache key from scheme colors
    cache_key = f"{scheme.bg_primary}_{scheme.text_primary}_{scheme.accent_color}_v2"
    
    # Return cached stylesheet if available
    if cache_key in _stylesheet_cache:
        return _stylesheet_cache[cache_key]
    
    # Generate new stylesheet
    stylesheet = f"""
    /* Main Application */
    QMainWindow, QWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        font-family: "Segoe UI", "Roboto", sans-serif;
    }}
    
    /* Tabs - Minimal underline style */
    QTabWidget::pane {{
        border: none;
        background-color: {scheme.bg_primary};
        border-top: 2px solid {scheme.border_color};
    }}

    QTabBar {{
        background-color: transparent;
        border: none;
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {scheme.text_secondary};
        padding: 12px 24px;
        border: 2px solid transparent;
        border-radius: 6px;
        margin-right: 8px;
        font-weight: 500;
        min-width: 80px;
    }}

    QTabBar::tab:selected {{
        color: {scheme.accent_color};
        border: 2px solid {scheme.accent_color};
        background-color: rgba(255, 255, 255, 0.03);
        font-weight: 600;
    }}

    QTabBar::tab:hover:!selected {{
        color: {scheme.text_primary};
        background-color: rgba(255, 255, 255, 0.05);
        border: 2px solid {scheme.border_color};
    }}

    QTabBar::tab:focus {{
        outline: none;
    }}
    
    /* Language Cards - Modern card design */
    QFrame#LanguageCard {{
        background-color: {scheme.bg_secondary};
        border: 1px solid {scheme.border_color};
        border-radius: 12px;
    }}
    
    QFrame#LanguageCard:hover {{
        border-color: {scheme.accent_color};
        background-color: {scheme.bg_tertiary};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {scheme.button_hover};
        border-color: {scheme.accent_color};
    }}
    
    QPushButton:pressed {{
        background-color: {scheme.bg_tertiary};
        border-color: {scheme.accent_color};
    }}
    
    QPushButton:disabled {{
        color: {scheme.text_disabled};
        background-color: {scheme.bg_secondary};
        border-color: {scheme.border_color};
    }}
    
    /* Text Edits */
    QTextEdit, QPlainTextEdit {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        border-radius: 6px;
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
        padding: 8px;
    }}
    
    /* List Widgets */
    QListWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        border-radius: 6px;
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
        outline: none;
    }}
    
    QListWidget::item {{
        padding: 4px;
        border-radius: 4px;
    }}
    
    QListWidget::item:hover {{
        background-color: {scheme.bg_tertiary};
    }}
    
    QListWidget::item:selected {{
        background-color: {scheme.bg_tertiary};
        border: 1px solid {scheme.accent_color};
    }}
    
    /* Tree Widgets */
    QTreeWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        border-radius: 6px;
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
        outline: none;
    }}
    
    QTreeWidget::item {{
        padding: 4px;
    }}
    
    QTreeWidget::item:hover {{
        background-color: {scheme.bg_tertiary};
    }}
    
    QTreeWidget::item:selected {{
        background-color: {scheme.bg_tertiary};
        color: {scheme.text_primary};
    }}
    
    /* Combo Boxes */
    QComboBox {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 6px 12px;
        border-radius: 6px;
    }}
    
    QComboBox:hover {{
        border-color: {scheme.accent_color};
        background-color: {scheme.button_hover};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 12px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        selection-background-color: {scheme.accent_color};
        selection-color: {scheme.text_primary};
        outline: none;
    }}
    
    /* Spin Boxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {scheme.button_bg};
        color: {scheme.text_primary};
        border: 1px solid {scheme.border_color};
        padding: 6px;
        border-radius: 6px;
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
        width: 18px;
        height: 18px;
        border: 1px solid {scheme.border_color};
        border-radius: 4px;
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
        border-radius: 8px;
        margin-top: 16px;
        padding-top: 12px;
        font-weight: bold;
    }}
    
    QGroupBox::title {{
        color: {scheme.accent_color};
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background-color: {scheme.bg_primary};
    }}
    
    /* Labels */
    QLabel {{
        color: {scheme.text_primary};
    }}
    
    /* Scroll Bars */
    QScrollBar:vertical {{
        background-color: {scheme.bg_primary};
        width: 10px;
        margin: 0;
        border-radius: 5px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {scheme.border_color};
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {scheme.accent_color};
    }}
    
    QScrollBar:horizontal {{
        background-color: {scheme.bg_primary};
        height: 10px;
        margin: 0;
        border-radius: 5px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {scheme.border_color};
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {scheme.accent_color};
    }}
    
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    
    QScrollBar::add-page, QScrollBar::sub-page {{
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
        width: 2px;
    }}
    
    QSplitter::handle:hover {{
        background-color: {scheme.accent_color};
    }}
    
    /* Menu Bar */
    QMenuBar {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_primary};
        border-bottom: 1px solid {scheme.border_color};
    }}
    
    QMenuBar::item {{
        padding: 6px 10px;
        background: transparent;
    }}
    
    QMenuBar::item:selected {{
        background-color: {scheme.bg_tertiary};
        border-radius: 4px;
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {scheme.bg_secondary};
        color: {scheme.text_secondary};
        border-top: 1px solid {scheme.border_color};
    }}
    """
    
    # Cache the generated stylesheet
    _stylesheet_cache[cache_key] = stylesheet
    
    return stylesheet


def apply_theme_to_app(app, scheme: ColorScheme):
    """Apply color scheme to entire QApplication.
    
    Args:
        app: QApplication instance
        scheme: ColorScheme to apply
    """
    stylesheet = generate_app_stylesheet(scheme)
    app.setStyleSheet(stylesheet)
