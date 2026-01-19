Release v1.0.0 - Major UI Refinements and Feature Additions

## 🎉 What's New

### ✨ New Features
- **Ctrl+F Search Shortcut**: Universal search shortcut now works across all tabs with search functionality (Folders, Editor, Shortcuts, and Settings tabs)
- **Enhanced Button Styling**: Refined folder management buttons with improved visual hierarchy
  - "Add Folder" button now uses success color (green) with white icon outline
  - "Remove Folder" button uses danger color (red) with white icon outline
  - Removed button borders for a cleaner, modern look

### 🎨 UI/UX Improvements
- **Professional README**: Complete rewrite with better structure, visual hierarchy, and comprehensive feature documentation
  - Added all screenshots in organized table layout
  - Included all demo videos showcasing key features
  - Improved "indie professional" tone throughout
  - Added clear calls-to-action for starring the repository
- **Icon System Enhancement**: Added `outline_color` parameter to icon rendering system for better visual contrast
- **Shortcuts Tab**: Added Ctrl+F to the in-app keyboard shortcuts reference

### 🐛 Bug Fixes
- Fixed theme application issues in `FoldersTab`
- Resolved test failures related to folder metadata handling
- Fixed file tree lazy loading for small datasets
- Corrected profile selector widget functionality
- Fixed multiple test suite regressions

### 🧪 Testing
- Updated test suite to handle new folder metadata structure (517 tests passing)
- Fixed theme-related test failures
- Improved test compatibility with dynamic theme system
- Added backward compatibility for folder data structures

### 📚 Documentation
- Updated README with modern layout and all visual assets
- Added Ctrl+F shortcut to keyboard shortcuts documentation
- Improved setup instructions with clearer uv installation guidance
- Added large codebase support documentation

### 🧹 Code Quality
- Removed obsolete test files (`large_test.py`, `test_db.py`)
- Moved `test_profile_cropper.py` to `tools/` directory for better organization
- Cleaned up project root directory structure

## 📦 Downloads

**Windows**: `dev_type_v1.0.0.exe` (Portable executable)  
**Linux**: `dev_type_v1.0.0.deb` (Debian/Ubuntu package)

## 🔧 Technical Details

### Breaking Changes
- None - this release is fully backward compatible

### Dependencies
- Python 3.13+
- PySide6 >= 6.10.0
- All other dependencies remain unchanged

### Known Issues
- None at this time

## 🙏 Acknowledgments

Special thanks to all contributors and users who provided feedback during development.

---

**Full Changelog**: Compare changes from previous version to v1.0.0
