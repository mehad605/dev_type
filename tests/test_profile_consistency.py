"""Integration test for profile switching consistency."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.ghost_manager import get_ghost_manager
from app.sound_manager import get_sound_manager
from app.profile_manager import ProfileManager
import app.ghost_manager as ghost_mod
import app.sound_manager as sound_mod

@pytest.fixture
def multi_profile_env(tmp_path):
    """Setup environment with two profiles."""
    data_dir = tmp_path / "Dev_Type_Data"
    data_dir.mkdir()
    
    with patch("app.portable_data.get_data_manager") as mock_gdm:
        from app.portable_data import PortableDataManager, _portable_data_manager
        # Standard way to get the singleton
        pdm = PortableDataManager()
        # Force the data dir for testing
        pdm._data_dir = data_dir
        pdm._detect_and_setup = lambda: None # Don't re-detect
        mock_gdm.return_value = pdm
        # Also set the global singleton
        _portable_data_manager = pdm

        pm = ProfileManager()
        pm.create_profile("User1")
        pm.create_profile("User2")

        # Ensure profile directories exist
        profile_dir = data_dir / "profiles"
        profile_dir.mkdir(exist_ok=True)
        (profile_dir / "User1").mkdir(exist_ok=True)
        (profile_dir / "User2").mkdir(exist_ok=True)

        yield pm, pdm

def test_ghost_manager_switches_directory(multi_profile_env):
    """VERIFY BUG: GhostManager should point to active profile's ghosts."""
    pm, pdm = multi_profile_env

    # Reset ghost manager singleton to ensure fresh instance
    from app import ghost_manager
    ghost_manager._ghost_manager = None

    # 1. Start with User1
    pm.switch_profile("User1")
    gm = get_ghost_manager()
    expected_g1 = pdm.get_active_profile_dir() / "ghosts"
    assert gm.ghosts_dir == expected_g1
    
    # 2. Switch to User2
    pm.switch_profile("User2")
    gm.refresh() # Simulating ui_main.py behavior
    
    # EXPECTED: gm.ghosts_dir should be User2's
    expected_g2 = pdm.get_active_profile_dir() / "ghosts"
    assert gm.ghosts_dir == expected_g2

def test_sound_manager_reloads_custom_metadata(multi_profile_env):
    """VERIFY FIX: SoundManager should reload custom profiles from active DB."""
    pm, pdm = multi_profile_env
    
    # 1. Setup User1 with a custom sound profile in their DB
    pm.switch_profile("User1")
    sm = get_sound_manager()
    sm.refresh()
    
    with patch("app.settings.get_setting", return_value='{"p1": {"name": "P1 Sound"}}'):
        sm.refresh()
        assert "p1" in sm.custom_profiles
        
    # 2. Switch to User2
    pm.switch_profile("User2")
    
    # VERIFY FIX: Calling refresh() loads User2's settings
    with patch("app.settings.get_setting", return_value='{"p2": {"name": "P2 Sound"}}'):
        sm.refresh()
        assert "p2" in sm.custom_profiles
        assert "p1" not in sm.custom_profiles

def test_folder_persistence_isolation(multi_profile_env):
    """VERIFY: Project folders are isolated between profiles."""
    pm, pdm = multi_profile_env
    from app import settings
    
    # 1. Profile 1: Add a folder
    pm.switch_profile("User1")
    settings.init_db(str(pm.get_current_db_path()))
    settings.add_folder("/path/to/project1")
    assert "/path/to/project1" in settings.get_folders()
    
    # 2. Profile 2: Should be empty
    pm.switch_profile("User2")
    settings.init_db(str(pm.get_current_db_path()))
    assert "/path/to/project1" not in settings.get_folders()
    assert len(settings.get_folders()) == 0
    
    # 3. Profile 1: Should still be there
def test_active_profile_rename_continuity(multi_profile_env):
    """VERIFY: Renaming active profile updates DB path in settings."""
    pm, pdm = multi_profile_env
    from app import settings
    
    # 1. Start on Alice
    pm.switch_profile("User1")
    settings.init_db(str(pm.get_current_db_path()))
    settings.set_setting("test_key", "AliceValue")
    
    # 2. Rename Alice to Bob
    pm.rename_profile("User1", "User2_Renamed")
    # In the app, MainWindow._on_profile_updated handles this by passing explicit path:
    settings.init_db(str(pm.get_current_db_path()))
    
    # Let's check the current path in settings
    from app.settings import _current_db_path
    assert "User2_Renamed" in str(_current_db_path)
