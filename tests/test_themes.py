"""Tests for theme application and color scheme management."""
import pytest
from app.themes import (
    get_color_scheme, 
    generate_app_stylesheet,
    NORD_DARK,
    CATPPUCCIN_DARK,
    DRACULA_DARK,
    LIGHT_THEME
)


def test_get_nord_theme():
    """Test getting Nord dark theme."""
    scheme = get_color_scheme("dark", "nord")
    assert scheme == NORD_DARK
    assert scheme.bg_primary == "#2e3440"
    assert scheme.text_correct == "#a3be8c"
    assert scheme.accent_color == "#5e81ac"


def test_get_catppuccin_theme():
    """Test getting Catppuccin dark theme."""
    scheme = get_color_scheme("dark", "catppuccin")
    assert scheme == CATPPUCCIN_DARK
    assert scheme.bg_primary == "#1e1e2e"
    assert scheme.text_correct == "#a6e3a1"
    assert scheme.accent_color == "#89b4fa"


def test_get_dracula_theme():
    """Test getting Dracula dark theme."""
    scheme = get_color_scheme("dark", "dracula")
    assert scheme == DRACULA_DARK
    assert scheme.bg_primary == "#282a36"
    assert scheme.text_correct == "#50fa7b"
    assert scheme.accent_color == "#bd93f9"


def test_get_light_theme():
    """Test getting light theme."""
    scheme = get_color_scheme("light", "nord")  # Scheme ignored for light
    assert scheme == LIGHT_THEME
    assert scheme.bg_primary == "#ffffff"
    assert scheme.text_primary == "#212121"


def test_default_to_nord():
    """Test that invalid scheme defaults to Nord."""
    scheme = get_color_scheme("dark", "invalid_scheme")
    assert scheme == NORD_DARK


def test_all_themes_have_required_colors():
    """Test that all themes have all required color attributes."""
    required_attrs = [
        'bg_primary', 'bg_secondary', 'bg_tertiary',
        'text_primary', 'text_secondary', 'text_disabled',
        'text_untyped', 'text_correct', 'text_incorrect', 'text_paused', 'cursor_color',
        'border_color', 'accent_color', 'button_bg', 'button_hover',
        'success_color', 'warning_color', 'error_color', 'info_color'
    ]
    
    themes = [NORD_DARK, CATPPUCCIN_DARK, DRACULA_DARK, LIGHT_THEME]
    for theme in themes:
        for attr in required_attrs:
            assert hasattr(theme, attr), f"Theme missing {attr}"
            value = getattr(theme, attr)
            assert value.startswith("#"), f"{attr} should be hex color"
            assert len(value) == 7, f"{attr} should be 7 chars (#RRGGBB)"


def test_stylesheet_generation():
    """Test that stylesheet is generated without errors."""
    scheme = NORD_DARK
    stylesheet = generate_app_stylesheet(scheme)
    
    # Check that key elements are in stylesheet
    assert "QMainWindow" in stylesheet
    assert "QPushButton" in stylesheet
    assert "QTextEdit" in stylesheet
    assert "QTabWidget" in stylesheet
    assert "QListWidget" in stylesheet
    
    # Check that colors are applied
    assert scheme.bg_primary in stylesheet
    assert scheme.text_primary in stylesheet
    assert scheme.accent_color in stylesheet
    assert scheme.border_color in stylesheet


def test_stylesheet_has_all_widgets():
    """Test that stylesheet covers all major widget types."""
    stylesheet = generate_app_stylesheet(NORD_DARK)
    
    widgets = [
        "QMainWindow", "QPushButton", "QTextEdit", "QListWidget",
        "QTreeWidget", "QComboBox", "QSpinBox", "QCheckBox",
        "QGroupBox", "QLabel", "QScrollBar", "QScrollArea",
        "QMessageBox", "QSplitter", "QMenuBar", "QStatusBar"
    ]
    
    for widget in widgets:
        assert widget in stylesheet, f"Stylesheet missing {widget} styles"


def test_color_consistency():
    """Test that typing colors are consistent across themes."""
    themes = [
        ("nord", NORD_DARK),
        ("catppuccin", CATPPUCCIN_DARK),
        ("dracula", DRACULA_DARK),
    ]
    
    for name, theme in themes:
        # All dark themes should have distinct colors
        colors = [
            theme.text_untyped,
            theme.text_correct,
            theme.text_incorrect,
            theme.text_paused
        ]
        # Check no duplicates
        assert len(colors) == len(set(colors)), f"{name} has duplicate typing colors"


def test_theme_accessibility():
    """Test that themes have sufficient contrast for readability."""
    # Simple hex to luminance check
    def hex_to_luminance(hex_color):
        """Calculate relative luminance (simplified)."""
        r = int(hex_color[1:3], 16) / 255
        g = int(hex_color[3:5], 16) / 255
        b = int(hex_color[5:7], 16) / 255
        return 0.299 * r + 0.587 * g + 0.114 * b
    
    # Check dark themes have light text on dark bg
    for theme in [NORD_DARK, CATPPUCCIN_DARK, DRACULA_DARK]:
        bg_lum = hex_to_luminance(theme.bg_primary)
        text_lum = hex_to_luminance(theme.text_primary)
        assert text_lum > bg_lum, "Dark theme should have lighter text than bg"
    
    # Check light theme has dark text on light bg
    bg_lum = hex_to_luminance(LIGHT_THEME.bg_primary)
    text_lum = hex_to_luminance(LIGHT_THEME.text_primary)
    assert text_lum < bg_lum, "Light theme should have darker text than bg"


def test_is_valid_hex_color_valid_6_char():
    """Test valid 6-character hex colors."""
    from app.themes import is_valid_hex_color
    assert is_valid_hex_color("#FF0000") is True
    assert is_valid_hex_color("#00ff00") is True
    assert is_valid_hex_color("#aAbBcC") is True
    assert is_valid_hex_color("#000000") is True
    assert is_valid_hex_color("#FFFFFF") is True


def test_is_valid_hex_color_valid_3_char():
    """Test valid 3-character hex colors."""
    from app.themes import is_valid_hex_color
    assert is_valid_hex_color("#F00") is True
    assert is_valid_hex_color("#abc") is True
    assert is_valid_hex_color("#123") is True


def test_is_valid_hex_color_invalid():
    """Test invalid hex colors."""
    from app.themes import is_valid_hex_color
    assert is_valid_hex_color("FF0000") is False  # No #
    assert is_valid_hex_color("#GGGGGG") is False  # Invalid chars
    assert is_valid_hex_color("#FF00") is False  # Wrong length (4 chars)
    assert is_valid_hex_color("#FF00000") is False  # Wrong length (7 chars)
    assert is_valid_hex_color("red") is False  # Color name
    assert is_valid_hex_color("") is False
    assert is_valid_hex_color(None) is False
    assert is_valid_hex_color(123) is False


def test_validate_hex_color_returns_valid():
    """Test validate_hex_color returns valid color."""
    from app.themes import validate_hex_color
    assert validate_hex_color("#FF0000", "#000000") == "#FF0000"
    assert validate_hex_color("#abc", "#000000") == "#abc"


def test_validate_hex_color_returns_default():
    """Test validate_hex_color returns default for invalid."""
    from app.themes import validate_hex_color
    assert validate_hex_color("invalid", "#FFFFFF") == "#FFFFFF"
    assert validate_hex_color("#GGGGGG", "#00FF00") == "#00FF00"
    assert validate_hex_color("", "#0000FF") == "#0000FF"
