"""
Instant splash screen using Tkinter.

Shows immediately before heavy Qt imports to provide instant visual feedback.
Designed to match the app's theme and provide a polished loading experience.
"""
import sqlite3
from pathlib import Path
from typing import Optional


class InstantSplash:
    """A polished splash screen using only Tkinter (no Qt dependencies)."""
    
    def __init__(self):
        self._root = None
        self._progress_canvas = None
        self._progress_rect = None
        self._status_label = None
        self._bar_width = 360
        self._bar_height = 8
        self._progress = 0
        
    def _get_theme_colors(self) -> dict:
        """Load theme colors from database, with Dracula as fallback."""
        # Default colors (Dracula - matches themes.py DRACULA_DARK)
        colors = {
            "bg": "#282a36",
            "border": "#bd93f9",  # accent_color (purple)
            "title": "#f8f8f2",  # text_primary
            "subtitle": "#bd93f9",  # accent_color
            "status": "#6272a4",  # text_disabled (comment)
            "progress_bg": "#44475a",  # bg_tertiary
            "progress_fill": "#bd93f9",  # accent_color
        }
        
        try:
            import sys
            from pathlib import Path
            
            # Try to find the database using portable data manager logic
            # First check if running from frozen executable
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller bundle
                exe_dir = Path(sys.executable).parent
            else:
                # Running from source
                exe_dir = Path(__file__).parent.parent
            
            # Look for Dev_Type_Data next to executable/source
            db_path = exe_dir / "Dev_Type_Data" / "typing_stats.db"
            
            if not db_path.exists():
                # Fallback to current directory
                db_path = Path("Dev_Type_Data/typing_stats.db")
            
            if not db_path.exists():
                return colors
                
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            cur.execute("SELECT value FROM settings WHERE key='dark_scheme'")
            row = cur.fetchone()
            scheme = row[0] if row else "dracula"
            
            conn.close()
            
            # Theme color mappings - directly from themes.py ColorScheme definitions
            schemes = {
                # Dracula (DRACULA_DARK)
                "dracula": {
                    "bg": "#282a36",  # bg_primary
                    "border": "#bd93f9",  # accent_color (purple)
                    "title": "#f8f8f2",  # text_primary
                    "subtitle": "#bd93f9",  # accent_color
                    "status": "#6272a4",  # text_disabled (comment)
                    "progress_bg": "#44475a",  # bg_tertiary
                    "progress_fill": "#bd93f9",  # accent_color
                },
                # Nord (NORD_DARK)
                "nord": {
                    "bg": "#2e3440",  # bg_primary (nord0)
                    "border": "#88c0d0",  # cursor_color (nord8 cyan)
                    "title": "#eceff4",  # text_primary (nord6)
                    "subtitle": "#81a1c1",  # info_color (nord9)
                    "status": "#d8dee9",  # text_secondary (nord4)
                    "progress_bg": "#434c5e",  # bg_tertiary (nord2)
                    "progress_fill": "#5e81ac",  # accent_color (nord10 blue)
                },
                # Catppuccin Mocha (CATPPUCCIN_DARK)
                "catppuccin": {
                    "bg": "#1e1e2e",  # bg_primary (base)
                    "border": "#89b4fa",  # accent_color (blue)
                    "title": "#cdd6f4",  # text_primary (text)
                    "subtitle": "#89b4fa",  # accent_color (blue)
                    "status": "#bac2de",  # text_secondary (subtext1)
                    "progress_bg": "#313244",  # bg_tertiary (surface0)
                    "progress_fill": "#89b4fa",  # accent_color (blue)
                },
                # Cyberpunk (CYBERPUNK_DARK)
                "cyberpunk": {
                    "bg": "#0b0c15",  # bg_primary
                    "border": "#ff003c",  # accent_color (neon red)
                    "title": "#00ff9f",  # text_primary (neon green)
                    "subtitle": "#00b8ff",  # text_secondary (neon blue)
                    "status": "#00b8ff",  # info_color (neon blue)
                    "progress_bg": "#2a2d3e",  # bg_tertiary
                    "progress_fill": "#ff003c",  # accent_color (neon red)
                },
                # Monokai Pro (MONOKAI_PRO)
                "monokai_pro": {
                    "bg": "#2D2A2E",  # bg_primary
                    "border": "#FFD866",  # accent_color (yellow)
                    "title": "#FCFCFA",  # text_primary
                    "subtitle": "#FFD866",  # accent_color
                    "status": "#939293",  # text_secondary
                    "progress_bg": "#403E41",  # bg_secondary
                    "progress_fill": "#FFD866",  # accent_color
                },
                # Gruvbox (GRUVBOX_DARK)
                "gruvbox": {
                    "bg": "#282828",  # bg_primary
                    "border": "#fe8019",  # cursor_color (orange)
                    "title": "#ebdbb2",  # text_primary
                    "subtitle": "#d3869b",  # accent_color (purple)
                    "status": "#a89984",  # text_secondary
                    "progress_bg": "#3c3836",  # bg_secondary
                    "progress_fill": "#d3869b",  # accent_color
                },
                # Solarized Dark (SOLARIZED_DARK)
                "solarized_dark": {
                    "bg": "#002b36",  # bg_primary
                    "border": "#268bd2",  # accent_color (blue)
                    "title": "#839496",  # text_primary
                    "subtitle": "#268bd2",  # accent_color
                    "status": "#586e75",  # text_secondary
                    "progress_bg": "#073642",  # bg_secondary
                    "progress_fill": "#268bd2",  # accent_color
                },
            }
            
            if scheme in schemes:
                colors = schemes[scheme]
                
        except Exception:
            pass  # Use defaults
            
        return colors
    
    def show(self) -> bool:
        """
        Show the splash screen.
        
        Returns True if successful, False if Tkinter unavailable.
        """
        try:
            import tkinter as tk
            from tkinter import font as tkfont
        except ImportError:
            return False
            
        try:
            colors = self._get_theme_colors()
            
            # Create the window
            self._root = tk.Tk()
            self._root.withdraw()  # Hide initially
            
            # Window dimensions
            width, height = 500, 280
            
            # Get screen dimensions and center
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            
            # Configure window
            self._root.geometry(f"{width}x{height}+{x}+{y}")
            self._root.overrideredirect(True)  # Frameless
            self._root.configure(bg=colors["border"])
            self._root.attributes("-topmost", True)
            
            # Main content frame (with border effect via padding)
            content = tk.Frame(self._root, bg=colors["bg"])
            content.pack(fill="both", expand=True, padx=3, pady=3)
            
            # Icon and Title Container
            header_frame = tk.Frame(content, bg=colors["bg"])
            header_frame.pack(pady=(40, 10))
            
            # Try to load the app icon
            icon_label = None
            try:
                import sys
                
                # Find icon path - try multiple locations
                icon_path = None
                
                if getattr(sys, 'frozen', False):
                    # Running from PyInstaller bundle
                    base_path = Path(sys._MEIPASS)
                    # Try different possible locations
                    possible_paths = [
                        base_path / "assets" / "icon.png",
                        base_path / "icon.png",
                    ]
                else:
                    # Running from source
                    base_path = Path(__file__).parent.parent
                    possible_paths = [
                        base_path / "assets" / "icon.png",
                    ]
                
                # Find first existing path
                for path in possible_paths:
                    if path.exists():
                        icon_path = path
                        break
                
                if icon_path and icon_path.exists():
                    # Try PIL first (better quality)
                    try:
                        from PIL import Image, ImageTk
                        img = Image.open(icon_path)
                        img = img.resize((64, 64), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                    except ImportError:
                        # Fallback to Tkinter PhotoImage (no PIL needed)
                        photo = tk.PhotoImage(file=str(icon_path))
                        # Subsample to resize (Tkinter's way)
                        photo = photo.subsample(
                            max(1, photo.width() // 64),
                            max(1, photo.height() // 64)
                        )
                    
                    icon_label = tk.Label(
                        header_frame,
                        image=photo,
                        bg=colors["bg"]
                    )
                    icon_label.image = photo  # Keep a reference
                    icon_label.pack(side="left", padx=(0, 15))
            except Exception as e:
                # Debug: print error if running from source
                if not getattr(sys, 'frozen', False):
                    print(f"[Splash] Could not load icon: {e}")
                pass  # Fallback to text-only
            
            # Title
            try:
                title_font = tkfont.Font(family="Segoe UI", size=26, weight="bold")
            except:
                title_font = ("TkDefaultFont", 26, "bold")
            
            # If icon loaded, use just text. Otherwise use emoji
            title_text = "Dev Type" if icon_label else "⌨️  Dev Type"
            title = tk.Label(
                header_frame,
                text=title_text,
                font=title_font,
                fg=colors["title"],
                bg=colors["bg"]
            )
            title.pack(side="left")
            
            # Subtitle
            try:
                sub_font = tkfont.Font(family="Segoe UI", size=12)
            except:
                sub_font = ("TkDefaultFont", 12)
            
            subtitle = tk.Label(
                content,
                text="Practice coding by typing",
                font=sub_font,
                fg=colors["subtitle"],
                bg=colors["bg"]
            )
            subtitle.pack(pady=(0, 50))
            
            # Progress bar
            self._progress_canvas = tk.Canvas(
                content,
                width=self._bar_width,
                height=self._bar_height,
                bg=colors["progress_bg"],
                highlightthickness=0
            )
            self._progress_canvas.pack(pady=(0, 15))
            
            # Progress fill rectangle (starts empty)
            self._progress_rect = self._progress_canvas.create_rectangle(
                0, 0, 0, self._bar_height,
                fill=colors["progress_fill"],
                outline=""
            )
            
            # Status text
            try:
                status_font = tkfont.Font(family="Segoe UI", size=10)
            except:
                status_font = ("TkDefaultFont", 10)
            
            self._status_label = tk.Label(
                content,
                text="Starting...",
                font=status_font,
                fg=colors["status"],
                bg=colors["bg"]
            )
            self._status_label.pack(pady=(0, 30))
            
            # Show window and force update to display immediately
            self._root.deiconify()
            self._root.update()
            self._root.update_idletasks()
            
            return True
            
        except Exception as e:
            print(f"[Splash] Error creating splash: {e}")
            return False
    
    def update(self, status: str, progress: int):
        """Update the status text and progress bar."""
        if not self._root:
            return
            
        try:
            # Update status text
            if self._status_label:
                self._status_label.config(text=status)
            
            # Update progress bar
            if self._progress_canvas and self._progress_rect:
                self._progress = max(0, min(100, progress))
                fill_width = int((self._progress / 100) * self._bar_width)
                self._progress_canvas.coords(
                    self._progress_rect,
                    0, 0, fill_width, self._bar_height
                )
            
            # Force update to display changes immediately
            self._root.update()
            self._root.update_idletasks()
        except:
            pass
    
    def close(self):
        """Close and destroy the splash screen."""
        if self._root:
            try:
                self._root.destroy()
            except:
                pass
            self._root = None


def create_instant_splash() -> Optional[InstantSplash]:
    """
    Create and display an instant splash screen.
    
    Returns the splash instance if successful, None otherwise.
    """
    splash = InstantSplash()
    if splash.show():
        return splash
    return None
