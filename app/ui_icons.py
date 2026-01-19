from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtSvg import QSvgRenderer

# Colors from svg.html
COLORS = {
    "red": "#F7768E",
    "green": "#73DACA",
    "blue": "#7AA2F7",
    "orange": "#FF9E64",
    "purple": "#BB9AF7",
    "gray": "#A9B1D6",
}

# Icon paths from svg.html
ICON_PATHS = {
    "EDIT": {"color": "blue", "path": '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>'},
    "DELETE": {"color": "red", "path": '<polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line>'},
    "CLOSE": {"color": "gray", "path": '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>'},
    "BACK": {"color": "gray", "path": '<line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline>'},
    "PLUS": {"color": "green", "path": '<line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line>'},
    "SEARCH": {"color": "blue", "path": '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>'},
    "SETTINGS": {"color": "gray", "path": '<circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>'},
    "FOLDER": {"color": "blue", "path": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>'},
    "CLOCK": {"color": "purple", "path": '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>'},
    "CHART": {"color": "green", "path": '<line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line>'},
    "TYPING": {"color": "orange", "path": '<polyline points="4 7 4 4 20 4 20 7"></polyline><line x1="9" y1="20" x2="15" y2="20"></line><line x1="12" y1="4" x2="12" y2="20"></line>'},
    "CODE": {"color": "blue", "path": '<polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>'},
    "SOUND": {"color": "blue", "path": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>'},
    "DEATH": {"color": "red", "path": '<path d="M12 2a7 7 0 0 0-7 7c0 1.5.4 2.8 1.1 4L5 22h3v-2h2v2h4v-2h2v2h3l-1.1-9c.7-1.2 1.1-2.5 1.1-4a7 7 0 0 0-7-7zM9 9a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm6 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm-3 5h2v2h-4v-2h2z"></path>'},
    "INDENT": {"color": "blue", "path": '<polyline points="3 8 7 12 3 16"></polyline><line x1="21" y1="12" x2="11" y2="12"></line><line x1="21" y1="6" x2="11" y2="6"></line><line x1="21" y1="18" x2="11" y2="18"></line>'},
    "GHOST": {"color": "purple", "path": '<path d="M18 9a6 6 0 0 0-12 0v11l2-2 2 2 2-2 2 2 2-2 2 2V9z"></path><circle cx="9" cy="9" r="1"></circle><circle cx="15" cy="9" r="1"></circle>'},
    "ROTATE_CCW": {"color": "blue", "path": '<polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>'},
    "STOP": {"color": "red", "path": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'},
    "WARNING": {"color": "orange", "path": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>'},
    "TRASH": {"color": "red", "path": '<polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>'},
    "STREAK": {"color": "orange", "path": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.115.385-2.256 1-3.5a2.5 2.5 0 0 0 2.5 3.5z"></path>'},
    "CHECK": {"color": "green", "path": '<polyline points="20 6 9 17 4 12"></polyline>'},
    "ROCKET": {"color": "blue", "path": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.1 2.1 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-9.56 1.55 1.55 0 0 1 2.25 0h0a1.55 1.55 0 0 1 0 2.25 22 22 0 0 1-9.56 2z"></path><path d="M9 12l5.83 5.83a.5.5 0 0 0 .7.01L22 11.5l-6.5-6.5-6.34 6.47a.5.5 0 0 0 .01.7L9 12z"></path>'},
    "TARGET": {"color": "red", "path": '<circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle>'},
    "CALENDAR": {"color": "blue", "path": '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>'},
    "KEYBOARD": {"color": "gray", "path": '<rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect><line x1="6" y1="8" x2="6" y2="8"></line><line x1="10" y1="8" x2="10" y2="8"></line><line x1="14" y1="8" x2="14" y2="8"></line><line x1="18" y1="8" x2="18" y2="8"></line><line x1="6" y1="12" x2="6" y2="12"></line><line x1="10" y1="12" x2="10" y2="12"></line><line x1="14" y1="12" x2="14" y2="12"></line><line x1="18" y1="12" x2="18" y2="12"></line><line x1="6" y1="16" x2="6" y2="16"></line><line x1="10" y1="16" x2="10" y2="16"></line><line x1="14" y1="16" x2="14" y2="16"></line><line x1="18" y1="16" x2="18" y2="16"></line>'},
    "USER": {"color": "blue", "path": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>'},
    "SUM": {"color": "purple", "path": '<path d="M18 7H6l6 5-6 5h12"></path>'},
    "FILES": {"color": "gray", "path": '<path d="M20 7h-3a2 2 0 0 1-2-2V2"></path><path d="M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2Z"></path><path d="M3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"></path>'},
    "DOWNLOAD": {"color": "blue", "path": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="3" x2="12" y2="15"></line>'},
    "TERMINAL": {"color": "blue", "path": '<polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line>'},
    "HEART": {"color": "gray", "path": '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>'},
    "HEART_FILLED": {"color": "blue", "filled": True, "path": '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>'},
}

def get_svg_content(name: str, color_override=None) -> str:
    """Get the SVG content string for an icon name."""
    if name not in ICON_PATHS:
        return ""
    
    data = ICON_PATHS[name]
    color = color_override if color_override else COLORS[data["color"]]
    path = data["path"]
    fill = color if data.get("filled") else "none"
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="{fill}"
stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</svg>"""

def get_pixmap(name: str, size=24, color_override=None) -> QPixmap:
    """Get a QPixmap for an icon, rendered sharply at the requested size."""
    svg_content = get_svg_content(name, color_override)
    if not svg_content:
        return QPixmap()
    
    # Use QSvgRenderer to render the vector data directly at the target size
    # This prevents the blurriness caused by scaling a small rasterized image
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
    
    # Create pixmap with target size
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    # Enable anti-aliasing for smoother edges
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    
    return pixmap

def get_icon(name: str, color_override=None) -> QIcon:
    """Get a QIcon for an icon, using a high-res base for sharpness."""
    # Use 64x64 as base for icons to stay sharp even on High DPI displays
    pixmap = get_pixmap(name, size=64, color_override=color_override)
    return QIcon(pixmap)
