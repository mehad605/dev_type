"""Theme management with Nord, Catppuccin, and Dracula color schemes.

This module provides theme definitions and application logic for the typing app.
Themes include complete color schemes for UI elements, text editor, and all widgets.
"""
import logging
import re
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import app.settings as settings

logger = logging.getLogger(__name__)

# Cache for generated stylesheets to avoid regeneration
_stylesheet_cache: Dict[str, str] = {}

# Regex pattern for validating hex colors (#RGB or #RRGGBB)
_HEX_COLOR_PATTERN = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')


def is_valid_hex_color(color: str) -> bool:
    """Check if a string is a valid hex color.
    
    Args:
        color: String to validate
        
    Returns:
        True if valid hex color (#RGB or #RRGGBB), False otherwise
    """
    if not isinstance(color, str):
        return False
    return bool(_HEX_COLOR_PATTERN.match(color))


def validate_hex_color(color: str, default: str = "#FFFFFF") -> str:
    """Validate and return a hex color, falling back to default if invalid.
    
    Args:
        color: Color string to validate
        default: Default color to return if invalid
        
    Returns:
        Valid hex color string
    """
    if is_valid_hex_color(color):
        return color
    logger.warning(f"Invalid hex color '{color}', using default '{default}'")
    return default


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

    # Card/List specific
    card_bg: str  # Background for folders/language cards
    card_border: str  # Border for folders/language cards

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ColorScheme':
        """Create from dictionary."""
        # Filter out unknown keys to be safe
        known_keys = cls.__annotations__.keys()
        filtered_data = {k: v for k, v in data.items() if k in known_keys}
        # Provide defaults for missing keys (fallback to Dracula-ish)
        defaults = DRACULA_DARK.to_dict() if 'DRACULA_DARK' in globals() else {}
        for k in known_keys:
            if k not in filtered_data:
                filtered_data[k] = defaults.get(k, "#FF0000")
        return cls(**filtered_data)


# ... existing imports ...
from app.theme_data import RawPalette, adjust_color
from app.palettes import THEME_MAP, NORD

# Compatibility shim
THEMES = {
    "dark": {k: None for k in THEME_MAP.keys()} # Keys only, values are proxies
}

def get_available_schemes(theme_type: str = "dark") -> list[str]:
    """Get list of available built-in scheme names."""
    if theme_type == "dark":
        return list(THEME_MAP.keys())
    return []

# ... existing utilities ...

def create_from_palette(p: RawPalette) -> ColorScheme:
    """Derive a full ColorScheme from a minimalist RawPalette."""
    
    # Derived shades
    bg_tertiary = adjust_color(p.bg_surface, 1.1)     # Slightly lighter than surface
    border_col = adjust_color(p.bg_surface, 1.2)      # Visible border
    text_sec = p.fg_muted                             # Use muted for secondary text
    text_dis = adjust_color(p.fg_muted, 0.7)          # Darker muted for disabled
    
    # Button states
    btn_bg = p.bg_surface
    btn_hover = adjust_color(p.bg_surface, 1.15)
    
    return ColorScheme(
        # Backgrounds
        bg_primary=p.bg_base,
        bg_secondary=p.bg_surface,
        bg_tertiary=bg_tertiary,
        
        # Text
        text_primary=p.fg_main,
        text_secondary=text_sec,
        text_disabled=text_dis,
        
        # Typing colors
        text_untyped=p.fg_muted,
        text_correct=p.success,
        text_incorrect=p.error,
        text_paused=p.warning,
        cursor_color=p.accent,
        
        # UI colors
        border_color=border_col,
        accent_color=p.accent,
        button_bg=btn_bg,
        button_hover=btn_hover,
        
        # Status colors
        success_color=p.success,
        warning_color=p.warning,
        error_color=p.error,
        info_color=p.accent,  # Often same as accent
        
        # Card/List specific
        card_bg=p.bg_surface,
        card_border=border_col,
    )

def _get_custom_themes() -> Dict[str, Dict]:
    """Load custom themes from settings."""
    try:
        data = settings.get_setting("custom_themes", "{}")
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to load custom themes: {e}")
        return {}

def save_custom_theme(name: str, scheme: ColorScheme, type: str = "dark"):
    """Save a custom theme."""
    customs = _get_custom_themes()
    if type not in customs:
        customs[type] = {}
    
    customs[type][name] = scheme.to_dict()
    settings.set_setting("custom_themes", json.dumps(customs))

def delete_custom_theme(name: str, type: str = "dark"):
    """Delete a custom theme."""
    customs = _get_custom_themes()
    if type in customs and name in customs[type]:
        del customs[type][name]
        settings.set_setting("custom_themes", json.dumps(customs))

def get_color_scheme(theme: str = "dark", scheme: str = "nord") -> ColorScheme:
    """Get a color scheme by scheme name.
    
    Always returns a dark theme as light mode is removed.
    Checks custom themes first, then built-in palettes.
    """
    # Force dark theme base
    theme = "dark"
    
    # 1. Check custom themes (full ColorScheme dicts)
    customs = _get_custom_themes()
    if theme in customs and scheme in customs[theme]:
        return ColorScheme.from_dict(customs[theme][scheme])
    
    # 2. Check built-in palettes (RawPalette -> generator)
    raw_palette = THEME_MAP.get(scheme, NORD) # Default to Nord
    return create_from_palette(raw_palette)

def is_builtin_theme(theme: str, scheme: str) -> bool:
    """Check if a theme is built-in (and unmodified)."""
    customs = _get_custom_themes()
    if theme in customs and scheme in customs[theme]:
        return False # Overridden by custom
    
    return scheme in THEME_MAP


def generate_app_stylesheet(scheme: ColorScheme) -> str:
    """Generate complete Qt stylesheet for the application.
    
    Uses caching to avoid regenerating the same stylesheet multiple times.
    
    Args:
        scheme: ColorScheme to use
        
    Returns:
        Complete Qt stylesheet string
    """
    # Fetch font settings
    ui_family = settings.get_setting("ui_font_family", settings.get_default("ui_font_family"))
    ui_size = settings.get_setting("ui_font_size", settings.get_default("ui_font_size"))
    
    # Create cache key from all scheme colors and fonts to ensure updates
    colors_key = "|".join(f"{k}:{v}" for k, v in sorted(scheme.to_dict().items()))
    cache_key = f"{colors_key}|font:{ui_family}|size:{ui_size}"
    
    # Return cached stylesheet if available
    if cache_key in _stylesheet_cache:
        return _stylesheet_cache[cache_key]
    
    # Generate new stylesheet
    stylesheet = f"""
    /* Main Application */
    QMainWindow, QWidget {{
        background-color: {scheme.bg_primary};
        color: {scheme.text_primary};
        font-family: "{ui_family}", "Segoe UI", "Roboto", sans-serif;
        font-size: {ui_size}pt;
    }}
    
    /* Tabs - Minimal underline style */
    QTabWidget::pane {{
        border: none;
        background-color: {scheme.bg_primary};
        border-top: 1px solid {scheme.border_color};
    }}

    QTabBar {{
        background-color: transparent;
        border: none;
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {scheme.text_secondary};
        padding: 6px 12px;
        border: 1px solid transparent;
        border-radius: 4px;
        margin-right: 2px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        color: {scheme.accent_color};
        border: 1px solid {scheme.accent_color};
        background-color: rgba(255, 255, 255, 0.03);
        font-weight: 600;
    }}

    QTabBar::tab:hover:!selected {{
        color: {scheme.text_primary};
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid {scheme.border_color};
    }}

    QTabBar::tab:focus {{
        outline: none;
    }}
    
    /* Language Cards - Modern card design */
    QFrame#LanguageCard {{
        background-color: {scheme.card_bg};
        border: 1px solid {scheme.card_border};
        border-radius: 12px;
    }}
    
    QFrame#folderCard {{
        background-color: {scheme.card_bg};
        border: 1px solid {scheme.card_border};
        border-radius: 8px;
    }}
    
    QFrame#LanguageCard:hover {{
        border-color: {scheme.accent_color};
        background-color: {scheme.bg_tertiary};
    }}
    
    QFrame#LanguageCard:focus {{
        border-color: {scheme.accent_color};
        border-width: 2px;
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
