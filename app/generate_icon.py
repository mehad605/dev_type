"""
Convert SVG icon to PNG and ICO formats for use as application icon.
Run this script when you update the icon.svg file.
Generates icons in the assets/ folder.
"""
from pathlib import Path
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QSize
from PIL import Image


def convert_svg_to_png(svg_path: Path, png_path: Path, size: int = 256):
    """Convert SVG to PNG at specified size with high quality."""
    renderer = QSvgRenderer(str(svg_path))
    
    if not renderer.isValid():
        print(f"Error: Invalid SVG file: {svg_path}")
        return False
    
    # Create image with alpha channel and smooth rendering
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)  # Transparent background
    
    # Render SVG to image with antialiasing
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    renderer.render(painter)
    painter.end()
    
    # Save as high-quality PNG
    if image.save(str(png_path), "PNG", quality=100):
        print(f"✓ Created {png_path.name} ({size}x{size})")
        return True
    else:
        print(f"✗ Failed to save {png_path}")
        return False


def convert_svg_to_ico(svg_path: Path, ico_path: Path):
    """Convert SVG to ICO format with multiple sizes for Windows."""
    # Windows icon sizes - LARGEST FIRST (Windows uses first icon as default)
    # Including high-DPI sizes for modern displays
    sizes = [256, 128, 96, 64, 48, 40, 32, 24, 20, 16]
    images = []
    
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        print(f"Error: Invalid SVG file: {svg_path}")
        return False
    
    # Create temporary directory for PNG files
    temp_dir = ico_path.parent / "temp_ico"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        for size in sizes:
            # Create high-quality QImage with antialiasing
            image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
            image.fill(0)  # Transparent background
            
            # Render SVG with high quality settings
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
            renderer.render(painter)
            painter.end()
            
            # Save temporary PNG with maximum quality
            temp_png = temp_dir / f"icon_{size}.png"
            image.save(str(temp_png), "PNG", quality=100)
            
            # Load with PIL and keep in RGBA mode
            pil_image = Image.open(temp_png).convert('RGBA')
            images.append(pil_image)
        
        # Save as ICO with all sizes
        # Use the largest image as base and include all sizes
        images[0].save(
            str(ico_path),
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
        # Close PIL images to release file handles
        for img in images:
            img.close()
        
        print(f"✓ Created {ico_path.name} (sizes: {', '.join(map(str, sizes))})")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create ICO: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass  # Ignore cleanup errors


def main():
    """Generate icon files from SVG."""
    # Assets directory (one level up from app/)
    assets_dir = Path(__file__).parent.parent / "assets"
    svg_path = assets_dir / "icon.svg"
    
    if not svg_path.exists():
        print(f"Error: {svg_path} not found!")
        print(f"Expected location: {svg_path.absolute()}")
        return
    
    print(f"Converting {svg_path.name} from {assets_dir}...")
    print()
    
    # Generate PNG files at different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        png_path = assets_dir / f"icon_{size}.png"
        convert_svg_to_png(svg_path, png_path, size)
    
    # Create standard icon.png (256x256)
    icon_path = assets_dir / "icon.png"
    convert_svg_to_png(svg_path, icon_path, 256)
    
    print()
    
    # Create Windows ICO file
    ico_path = assets_dir / "icon.ico"
    convert_svg_to_ico(svg_path, ico_path)
    
    print()
    print("✓ Icon generation complete!")
    print(f"  All icons saved to: {assets_dir.absolute()}")
    print("  Files created:")
    print("    - icon.png (256x256)")
    print("    - icon_16.png through icon_256.png")
    print("    - icon.ico (Windows multi-size icon)")



if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    # QApplication needed for Qt graphics operations
    app = QApplication(sys.argv)
    main()
