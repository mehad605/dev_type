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
            
            # Nordic theme colors
            bg_color = "#2e3440"
            border_color = "#88c0d0"
            text_color = "#eceff4"
            subtitle_color = "#88c0d0"
            status_color = "#d8dee9"
            
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
                fg="#4c566a",
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
