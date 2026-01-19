"""
Core data structures for theme management.
"""
from dataclasses import dataclass

@dataclass
class RawPalette:
    """Minimal color palette definition provided by user/designer."""
    name: str
    bg_base: str    # Main background (darkest)
    bg_surface: str # Secondary background (panels, sidebars)
    fg_main: str    # Main text color
    fg_muted: str   # Secondary text / comments
    accent: str     # Primary accent color
    error: str      # Error/Deletion color
    success: str    # Success/Addition color
    warning: str    # Warning/Pause color

def adjust_color(hex_color: str, factor: float) -> str:
    """Adjust brightness of a hex color.
    
    Args:
        hex_color: e.g. "#RRGGBB"
        factor: >1.0 to lighten, <1.0 to darken
    
    Returns:
        New hex color string
    """
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Adjust
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color
