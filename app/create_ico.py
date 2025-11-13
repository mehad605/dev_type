"""
DEPRECATED: Use generate_icon.py instead.

This script has been replaced by generate_icon.py which:
- Converts SVG to PNG and ICO formats
- Saves icons to the assets/ folder
- Generates multiple sizes automatically

Run: python app/generate_icon.py
"""
from pathlib import Path
from PIL import Image


def create_ico():
    """Create multi-resolution ICO file from PNG.
    
    DEPRECATED: Use generate_icon.py instead.
    """
    print("⚠️  This script is deprecated!")
    print("   Use: python app/generate_icon.py")
    print()
    
    assets_dir = Path(__file__).parent.parent / "assets"
    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"
    
    if not png_path.exists():
        print(f"❌ {png_path} not found!")
        return False
    
    try:
        # Load the PNG
        img = Image.open(png_path)
        
        # Create ICO with multiple sizes for better quality
        # Windows uses different sizes for different contexts
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Resize and save as ICO
        img.save(
            ico_path,
            format='ICO',
            sizes=sizes
        )
        
        print(f"✅ Created {ico_path.name}")
        print(f"   Sizes: {', '.join(f'{w}x{h}' for w, h in sizes)}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating ICO: {e}")
        print("   Install Pillow: pip install pillow")
        return False


if __name__ == "__main__":
    create_ico()
