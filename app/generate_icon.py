"""
Convert SVG icon to PNG format for use as application icon.
Run this script when you update the icon.svg file.
"""
from pathlib import Path
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QSize


def convert_svg_to_png(svg_path: Path, png_path: Path, size: int = 256):
    """Convert SVG to PNG at specified size."""
    renderer = QSvgRenderer(str(svg_path))
    
    if not renderer.isValid():
        print(f"Error: Invalid SVG file: {svg_path}")
        return False
    
    # Create image with alpha channel
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(0)  # Transparent background
    
    # Render SVG to image
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    
    # Save as PNG
    if image.save(str(png_path), "PNG"):
        print(f"✓ Created {png_path.name} ({size}x{size})")
        return True
    else:
        print(f"✗ Failed to save {png_path}")
        return False


def main():
    """Generate icon files from SVG."""
    app_dir = Path(__file__).parent
    svg_path = app_dir / "icon.svg"
    
    if not svg_path.exists():
        print(f"Error: {svg_path} not found!")
        return
    
    print(f"Converting {svg_path.name}...")
    
    # Generate different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        png_path = app_dir / f"icon_{size}.png"
        convert_svg_to_png(svg_path, png_path, size)
    
    # Also create a standard icon.png
    icon_path = app_dir / "icon.png"
    convert_svg_to_png(svg_path, icon_path, 256)
    
    print("\n✓ Icon conversion complete!")
    print("  The application will use these icon files automatically.")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    # QApplication needed for Qt graphics operations
    app = QApplication(sys.argv)
    main()
