"""
Ultra-fast splash screen using tkinter.

Shows immediately before Qt/PySide6 imports to give instant visual feedback.
Falls back gracefully if tkinter is not available.
"""
import sys
from typing import Optional


class InstantSplash:
    """Minimal splash screen using tkinter for instant display."""
    
    def __init__(self):
        self.root: Optional[any] = None
        self.label: Optional[any] = None
        
    def show(self) -> bool:
        """
        Show the instant splash screen.
        
        Returns:
            True if splash was shown, False if tkinter not available
        """
        try:
            import tkinter as tk
            from tkinter import font
            
            # Create root window
            self.root = tk.Tk()
            self.root.title("")
            self.root.overrideredirect(True)  # No window decorations
            
            # Set size
            width, height = 450, 250
            
            # Center on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            
            # Load theme settings directly from DB to match user preference
            import sqlite3
            from pathlib import Path
            
            # Default colors (Nord)
            bg_color = "#2e3440"
            border_color = "#88c0d0"
            text_color = "#eceff4"
            subtitle_color = "#88c0d0"
            status_color = "#d8dee9"
            indicator_color = "#4c566a"
            
            try:
                # Try to find DB and load theme
                # We duplicate some logic from settings.py to avoid importing it (and Qt)
                db_path = Path("Dev_Type_Data/typing_stats.db")
                if not db_path.exists():
                    # Try parent dir (dev mode)
                    db_path = Path(__file__).parent.parent / "Dev_Type_Data" / "typing_stats.db"
                
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM settings WHERE key='theme'")
                    theme_row = cur.fetchone()
                    theme = theme_row[0] if theme_row else "dark"
                    
                    cur.execute("SELECT value FROM settings WHERE key='dark_scheme'")
                    scheme_row = cur.fetchone()
                    scheme = scheme_row[0] if scheme_row else "dracula"
                    conn.close()
                    
                    # Map common schemes to colors (simplified)
                    if theme == "light":
                        bg_color = "#ffffff"
                        border_color = "#bdbdbd"
                        text_color = "#212121"
                        subtitle_color = "#1976d2"
                        status_color = "#424242"
                        indicator_color = "#9e9e9e"
                    elif scheme == "dracula":
                        bg_color = "#282a36"
                        border_color = "#bd93f9"
                        text_color = "#f8f8f2"
                        subtitle_color = "#bd93f9"
                        status_color = "#f8f8f2"
                        indicator_color = "#6272a4"
                    elif scheme == "catppuccin":
                        bg_color = "#1e1e2e"
                        border_color = "#89b4fa"
                        text_color = "#cdd6f4"
                        subtitle_color = "#89b4fa"
                        status_color = "#bac2de"
                        indicator_color = "#585b70"
                    elif scheme == "cyberpunk":
                        bg_color = "#0b0c15"
                        border_color = "#ff003c"
                        text_color = "#00ff9f"
                        subtitle_color = "#00b8ff"
                        status_color = "#00ff9f"
                        indicator_color = "#565869"
                    elif scheme == "monokai_pro":
                        bg_color = "#2D2A2E"
                        border_color = "#FFD866"
                        text_color = "#FCFCFA"
                        subtitle_color = "#FFD866"
                        status_color = "#FCFCFA"
                        indicator_color = "#727072"
                    elif scheme == "gruvbox":
                        bg_color = "#282828"
                        border_color = "#d3869b"
                        text_color = "#ebdbb2"
                        subtitle_color = "#d3869b"
                        status_color = "#ebdbb2"
                        indicator_color = "#928374"
                    elif scheme == "solarized_dark":
                        bg_color = "#002b36"
                        border_color = "#268bd2"
                        text_color = "#839496"
                        subtitle_color = "#268bd2"
                        status_color = "#839496"
                        indicator_color = "#657b83"
            except Exception:
                pass  # Fallback to Nord defaults

            
            # Main frame with border
            main_frame = tk.Frame(
                self.root,
                bg=border_color,
                padx=3,
                pady=3
            )
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Content frame
            content_frame = tk.Frame(
                main_frame,
                bg=bg_color
            )
            content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # Title
            title_font = font.Font(family="Segoe UI", size=22, weight="bold")
            title = tk.Label(
                content_frame,
                text="⌨️ Dev Typing App",
                font=title_font,
                fg=text_color,
                bg=bg_color
            )
            title.pack(pady=(40, 10))
            
            # Subtitle
            subtitle_font = font.Font(family="Segoe UI", size=11)
            subtitle = tk.Label(
                content_frame,
                text="Practice coding by typing",
                font=subtitle_font,
                fg=subtitle_color,
                bg=bg_color
            )
            subtitle.pack(pady=(0, 20))
            
            # Status label (we'll update this)
            status_font = font.Font(family="Segoe UI", size=10)
            self.label = tk.Label(
                content_frame,
                text="Loading...",
                font=status_font,
                fg=status_color,
                bg=bg_color
            )
            self.label.pack(pady=(50, 10))
            
            # Loading indicator
            indicator_font = font.Font(family="Segoe UI", size=14)
            indicator = tk.Label(
                content_frame,
                text="•  •  •",
                font=indicator_font,
                fg=indicator_color,
                bg=bg_color
            )
            indicator.pack(pady=(0, 20))
            
            # Keep window on top
            self.root.attributes('-topmost', True)
            
            # Update to show
            self.root.update()
            
            return True
            
        except ImportError:
            # tkinter not available (rare on Windows/macOS)
            return False
        except Exception as e:
            print(f"[InstantSplash] Warning: Could not create splash: {e}")
            return False
    
    def update_status(self, text: str):
        """Update the status text."""
        if self.label and self.root:
            try:
                self.label.config(text=text)
                self.root.update()
            except:
                pass
    
    def close(self):
        """Close the splash screen."""
        if self.root:
            try:
                self.root.destroy()
                self.root = None
            except:
                pass


def create_instant_splash() -> Optional[InstantSplash]:
    """
    Create and show an instant splash screen.
    
    Returns:
        InstantSplash instance if successful, None otherwise
    """
    splash = InstantSplash()
    if splash.show():
        return splash
    return None
