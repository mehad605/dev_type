"""Tests for profile management and multi-user support."""
import pytest
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.profile_manager import ProfileManager, get_profile_manager
from app.portable_data import get_data_manager

@pytest.fixture
def temp_data_dir(tmp_path):
    """Set up a temporary Dev_Type_Data directory structure with full isolation."""
    import app.profile_manager
    import app.portable_data
    
    data_dir = tmp_path / "Dev_Type_Data"
    data_dir.mkdir()
    (data_dir / "profiles").mkdir()
    (data_dir / "shared").mkdir()
    
    # Mock data manager instance
    mock_dm_instance = MagicMock()
    mock_dm_instance.get_data_dir.return_value = data_dir
    mock_dm_instance.get_profiles_dir.return_value = data_dir / "profiles"
    mock_dm_instance.get_shared_dir.return_value = data_dir / "shared"
    mock_dm_instance.get_database_path.return_value = data_dir / "profiles" / "Default" / "typing_stats.db"
    
    # Patch both the getter in portable_data and the one imported in profile_manager
    with patch('app.portable_data.get_data_manager', return_value=mock_dm_instance), \
         patch('app.profile_manager.get_data_manager', return_value=mock_dm_instance):
        
        # Reset Singletons
        app.profile_manager._profile_manager = None
        app.profile_manager.ProfileManager._instance = None
        
        manager = app.profile_manager.ProfileManager()
        yield manager, data_dir

def test_profile_manager_singleton():
    """Test that ProfileManager follows singleton pattern."""
    ProfileManager._instance = None
    m1 = get_profile_manager()
    m2 = get_profile_manager()
    assert m1 is m2

def test_initial_structure_creation(temp_data_dir):
    """Test that basic profile structure is created on init."""
    manager, data_dir = temp_data_dir
    assert (data_dir / "profiles").exists()
    assert (data_dir / "shared").exists()
    assert (data_dir / "shared" / "global_config.json").exists()
    # Default profile should be created by migration logic if none exists
    assert (data_dir / "profiles" / "Default").exists()

def test_create_profile(temp_data_dir):
    """Test creating a new profile."""
    manager, data_dir = temp_data_dir

    # Create a temporary image file
    avatar_image = data_dir / "avatar.png"
    avatar_image.write_text("fake avatar data")
    success = manager.create_profile("Zoof", str(avatar_image))

    assert success is True
    assert (data_dir / "profiles" / "Zoof").exists()
    assert (data_dir / "profiles" / "Zoof" / "profile.json").exists()

    # Verify image was copied
    profile_pic = data_dir / "profiles" / "Zoof" / "profile_pic.jpg"
    assert profile_pic.exists()
    assert profile_pic.read_text() == "fake avatar data"

    # Verify metadata
    with open(data_dir / "profiles" / "Zoof" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] == str(profile_pic)

def test_create_duplicate_profile(temp_data_dir):
    """Test that duplicate profiles cannot be created."""
    manager, _ = temp_data_dir
    manager.create_profile("Duplicate")
    success = manager.create_profile("Duplicate")
    assert success is False

def test_get_all_profiles(temp_data_dir):
    """Test retrieving lists of profiles in order."""
    manager, _ = temp_data_dir
    manager.create_profile("A")
    manager.create_profile("B")
    
    profiles = manager.get_all_profiles()
    # Default + A + B = 3
    assert len(profiles) == 3
    names = [p["name"] for p in profiles]
    assert "Default" in names
    assert "A" in names
    assert "B" in names

def test_switch_profile(temp_data_dir):
    """Test switching active profiles."""
    manager, data_dir = temp_data_dir
    manager.create_profile("Gamer")
    
    with patch.object(manager, 'profile_switched') as mock_signal:
        manager.switch_profile("Gamer")
        assert manager.active_profile == "Gamer"
        mock_signal.emit.assert_called_with("Gamer")
        
    # Verify persistence in config
    with open(data_dir / "shared" / "global_config.json", "r") as f:
        config = json.load(f)
        assert config["active_profile"] == "Gamer"

def test_delete_profile(temp_data_dir):
    """Test deleting profiles."""
    manager, data_dir = temp_data_dir
    manager.create_profile("Temporary")
    
    success = manager.delete_profile("Temporary")
    assert success is True
    assert not (data_dir / "profiles" / "Temporary").exists()

def test_delete_only_profile_fails(temp_data_dir):
    """Test that you cannot delete the only profile."""
    manager, _ = temp_data_dir
    # Initially only "Default" exists
    success = manager.delete_profile("Default")
    assert success is False

def test_delete_active_profile_switches_to_default(temp_data_dir):
    """Test that deleting the active profile falls back to Default."""
    manager, _ = temp_data_dir
    manager.create_profile("ActiveOne")
    manager.switch_profile("ActiveOne")
    
    manager.delete_profile("ActiveOne")
    assert manager.active_profile == "Default"

def test_rename_profile(temp_data_dir):
    """Test renaming a profile folder and metadata."""
    manager, data_dir = temp_data_dir
    manager.create_profile("OldName")
    
    success = manager.rename_profile("OldName", "NewName")
    assert success is True
    assert not (data_dir / "profiles" / "OldName").exists()
    assert (data_dir / "profiles" / "NewName").exists()
    
    # If it was active, it should stay active with new name
    manager.switch_profile("NewName")
    manager.rename_profile("NewName", "RenamedActive")
    assert manager.active_profile == "RenamedActive"

def test_update_profile_image(temp_data_dir):
    """Test updating only the profile image."""
    manager, data_dir = temp_data_dir

    # Create a temporary image file
    old_image = data_dir / "old.png"
    old_image.write_text("fake image data")
    manager.create_profile("User", str(old_image))

    # Create new image file
    new_image = data_dir / "new.png"
    new_image.write_text("new fake image data")
    manager.update_profile_image("User", str(new_image))

    # Check that profile_pic.jpg was created and metadata updated
    profile_pic = data_dir / "profiles" / "User" / "profile_pic.jpg"
    assert profile_pic.exists()
    assert profile_pic.read_text() == "new fake image data"

    with open(data_dir / "profiles" / "User" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] == str(profile_pic)

def test_create_profile_without_image(temp_data_dir):
    """Test creating a profile without an image."""
    manager, data_dir = temp_data_dir

    success = manager.create_profile("NoImage", None)

    assert success is True
    assert (data_dir / "profiles" / "NoImage").exists()

    # Verify metadata has no image
    with open(data_dir / "profiles" / "NoImage" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] is None

    # No profile_pic.jpg should be created
    profile_pic = data_dir / "profiles" / "NoImage" / "profile_pic.jpg"
    assert not profile_pic.exists()


def test_update_profile_image_to_none(temp_data_dir):
    """Test updating a profile image to None removes the image file."""
    manager, data_dir = temp_data_dir

    # Create profile with image
    image_file = data_dir / "test.jpg"
    image_file.write_text("image content")
    manager.create_profile("TestProfile", str(image_file))

    # Verify image exists
    profile_pic = data_dir / "profiles" / "TestProfile" / "profile_pic.jpg"
    assert profile_pic.exists()

    # Update to None
    manager.update_profile_image("TestProfile", None)

    # Verify image file is removed and metadata updated
    assert not profile_pic.exists()

    with open(data_dir / "profiles" / "TestProfile" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] is None


def test_update_profile_image_nonexistent_file(temp_data_dir):
    """Test updating profile image with non-existent file does nothing."""
    manager, data_dir = temp_data_dir

    manager.create_profile("TestProfile", None)

    # Try to update with non-existent file
    manager.update_profile_image("TestProfile", "/nonexistent/path/image.png")

    # Verify no image file created and metadata unchanged
    profile_pic = data_dir / "profiles" / "TestProfile" / "profile_pic.jpg"
    assert not profile_pic.exists()

    with open(data_dir / "profiles" / "TestProfile" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] is None


def test_rename_profile_preserves_image(temp_data_dir):
    """Test that renaming a profile preserves the copied image."""
    manager, data_dir = temp_data_dir

    # Create profile with image
    image_file = data_dir / "avatar.gif"
    image_file.write_text("gif content")
    manager.create_profile("OldName", str(image_file))

    # Verify image was copied
    old_profile_pic = data_dir / "profiles" / "OldName" / "profile_pic.jpg"
    assert old_profile_pic.exists()
    assert old_profile_pic.read_text() == "gif content"

    # Rename profile
    success = manager.rename_profile("OldName", "NewName")
    assert success is True

    # Verify image is preserved in new location
    new_profile_pic = data_dir / "profiles" / "NewName" / "profile_pic.jpg"
    assert new_profile_pic.exists()
    assert new_profile_pic.read_text() == "gif content"
    assert not old_profile_pic.exists()  # Old location should be gone

    # Verify metadata points to new location
    with open(data_dir / "profiles" / "NewName" / "profile.json", "r") as f:
        meta = json.load(f)
        assert meta["image"] == str(new_profile_pic)


def test_create_profile_image_different_extensions(temp_data_dir):
    """Test creating profiles with images of different file types."""
    manager, data_dir = temp_data_dir

    # Test with PNG
    png_file = data_dir / "avatar.png"
    png_file.write_text("png data")
    success_png = manager.create_profile("PngProfile", str(png_file))

    # Test with JPEG
    jpg_file = data_dir / "avatar.jpeg"
    jpg_file.write_text("jpeg data")
    success_jpg = manager.create_profile("JpgProfile", str(jpg_file))

    assert success_png is True
    assert success_jpg is True

    # Both should be copied as profile_pic.jpg
    png_pic = data_dir / "profiles" / "PngProfile" / "profile_pic.jpg"
    jpg_pic = data_dir / "profiles" / "JpgProfile" / "profile_pic.jpg"

    assert png_pic.exists()
    assert jpg_pic.exists()
    assert png_pic.read_text() == "png data"
    assert jpg_pic.read_text() == "jpeg data"


def test_rename_default_doesnt_create_new_default(temp_data_dir):
    """Test that renaming the Default profile doesn't create a new Default on restart."""
    manager, data_dir = temp_data_dir

    # Rename the Default profile to something else
    success = manager.rename_profile("Default", "MyProfile")
    assert success is True

    # Verify Default is gone and MyProfile exists
    assert not (data_dir / "profiles" / "Default").exists()
    assert (data_dir / "profiles" / "MyProfile").exists()

    # Simulate app restart by creating a new ProfileManager instance
    # (this should trigger migration logic check)
    import app.profile_manager
    app.profile_manager._profile_manager = None
    app.profile_manager.ProfileManager._instance = None

    new_manager = app.profile_manager.ProfileManager()

    # Check that no new Default profile was created
    profiles = new_manager.get_all_profiles()
    profile_names = [p["name"] for p in profiles]

    assert "Default" not in profile_names, "Should not create new Default profile after renaming"
    assert "MyProfile" in profile_names, "Renamed profile should still exist"


def test_migration_logic(tmp_path):
    """Test legacy data migration on first run."""
    data_dir = tmp_path / "MigrationData"
    data_dir.mkdir()
    
    # Simulate legacy state (typing_stats.db in root)
    legacy_db = data_dir / "typing_stats.db"
    legacy_db.write_text("dummy database content")
    
    legacy_ghosts = data_dir / "ghosts"
    legacy_ghosts.mkdir()
    (legacy_ghosts / "replay.json").write_text("{}")
    legacy_sounds = data_dir / "custom_sounds"
    legacy_sounds.mkdir()
    (legacy_sounds / "click.wav").touch()

    legacy_snapshot = data_dir / "language_snapshot.json"
    legacy_snapshot.write_text("{}")
    
    # Mock data manager
    with patch('app.profile_manager.get_data_manager') as mock_dm:
        mock_instance = MagicMock()
        mock_instance.get_data_dir.return_value = data_dir
        mock_instance.get_profiles_dir.return_value = data_dir / "profiles"
        mock_instance.get_shared_dir.return_value = data_dir / "shared"
        mock_dm.return_value = mock_instance
        
        import app.profile_manager
        app.profile_manager._profile_manager = None
        ProfileManager._instance = None
        manager = ProfileManager()
        
        # Verify migration
        assert (data_dir / "profiles" / "Default" / "typing_stats.db").exists()
        assert (data_dir / "profiles" / "Default" / "ghosts" / "replay.json").exists()
        assert (data_dir / "profiles" / "Default" / "language_snapshot.json").exists()
        assert (data_dir / "shared" / "sounds" / "custom" / "click.wav").exists()
        
        # Original should be gone
        assert not legacy_db.exists()
        assert not (data_dir / "ghosts").exists()
        assert not legacy_sounds.exists()
        assert not legacy_snapshot.exists()
