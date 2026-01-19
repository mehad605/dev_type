"""
Predefined color palettes for the application.
"""
from app.theme_data import RawPalette

# =============================================================================
# 1. NORD DARK
# Source: https://www.nordtheme.com/docs/colors-and-palettes
# =============================================================================
NORD = RawPalette(
    name="Nord",
    bg_base="#2e3440",    # nord0  (Polar Night)
    bg_surface="#3b4252", # nord1  (Darker UI elements)
    fg_main="#eceff4",    # nord6  (Snow Storm)
    fg_muted="#616e88",   # nord3  (Comments/Disabled)
    accent="#88c0d0",     # nord8  (Frost Cyan)
    error="#bf616a",      # nord11 (Aurora Red)
    success="#a3be8c",    # nord14 (Aurora Green)
    warning="#ebcb8b"     # nord13 (Aurora Yellow)
)

# =============================================================================
# 2. CATPPUCCIN MOCHA
# Source: https://github.com/catppuccin/catppuccin
# =============================================================================
CATPPUCCIN_MOCHA = RawPalette(
    name="Catppuccin Mocha",
    bg_base="#1e1e2e",    # Base
    bg_surface="#313244", # Surface0
    fg_main="#cdd6f4",    # Text
    fg_muted="#6c7086",   # Overlay0
    accent="#89b4fa",     # Blue
    error="#f38ba8",      # Red
    success="#a6e3a1",    # Green
    warning="#f9e2af"     # Yellow
)

# =============================================================================
# 3. DRACULA
# Source: https://draculatheme.com/spec
# =============================================================================
DRACULA = RawPalette(
    name="Dracula",
    bg_base="#282a36",    # Background
    bg_surface="#44475a", # Current Line
    fg_main="#f8f8f2",    # Foreground
    fg_muted="#6272a4",   # Comment
    accent="#bd93f9",     # Purple
    error="#ff5555",      # Red
    success="#50fa7b",    # Green
    warning="#f1fa8c"     # Yellow
)

# =============================================================================
# 4. MONOKAI PRO
# Source: https://monokai.pro/
# =============================================================================
MONOKAI_PRO = RawPalette(
    name="Monokai Pro",
    bg_base="#2d2a2e",    # Pro dark grey
    bg_surface="#403e41", # Lighter panel
    fg_main="#fcfcfa",    # White
    fg_muted="#727072",   # Grey
    accent="#ffd866",     # Yellow
    error="#ff6188",      # Red
    success="#a9dc76",    # Green
    warning="#fc9867"     # Orange
)

# =============================================================================
# 5. GRUVBOX DARK (Medium)
# Source: https://github.com/morhetz/gruvbox
# =============================================================================
GRUVBOX_DARK = RawPalette(
    name="Gruvbox Dark",
    bg_base="#282828",    # Dark1
    bg_surface="#3c3836", # Dark2
    fg_main="#ebdbb2",    # Light1
    fg_muted="#928374",   # Gray 244
    accent="#fe8019",     # Orange
    error="#fb4934",      # Red
    success="#b8bb26",    # Green
    warning="#fabd2f"     # Yellow
)

# =============================================================================
# 6. SOLARIZED DARK
# Source: https://ethanschoonover.com/solarized/
# =============================================================================
SOLARIZED_DARK = RawPalette(
    name="Solarized Dark",
    bg_base="#002b36",    # Base03
    bg_surface="#073642", # Base02
    fg_main="#839496",    # Base0
    fg_muted="#586e75",   # Base01
    accent="#268bd2",     # Blue
    error="#dc322f",      # Red
    success="#859900",    # Green
    warning="#b58900"     # Yellow
)

# =============================================================================
# 7. CYBERPUNK (2077 Inspired)
# Source: Based on Cyberpunk 2077 UI references
# =============================================================================
CYBERPUNK = RawPalette(
    name="Cyberpunk",
    bg_base="#050a0e",    # Deep Black
    bg_surface="#161822", # Panel
    fg_main="#00f0ff",    # Neon Cyan
    fg_muted="#565869",   # Grey
    accent="#fcee0a",     # Neon Yellow
    error="#ff003c",      # Neon Red
    success="#00ff9f",    # Neon Green
    warning="#fcee0a"     # Same as accent
)

ALL_THEMES = [NORD, CATPPUCCIN_MOCHA, DRACULA, MONOKAI_PRO, GRUVBOX_DARK, SOLARIZED_DARK, CYBERPUNK]

THEME_MAP = {
    "nord": NORD,
    "catppuccin": CATPPUCCIN_MOCHA,
    "dracula": DRACULA,
    "monokai_pro": MONOKAI_PRO,
    "gruvbox": GRUVBOX_DARK,
    "solarized_dark": SOLARIZED_DARK,
    "cyberpunk": CYBERPUNK,
}
