import tempfile
from pathlib import Path
import app.settings as settings


def test_settings_db_roundtrip(tmp_path: Path):
    db_file = tmp_path / "data.db"
    # init
    settings.init_db(str(db_file))
    # default setting exists
    val = settings.get_setting("theme", "")
    assert val in ("dark", "")
    # set and get
    settings.set_setting("test_key", "value1")
    assert settings.get_setting("test_key") == "value1"
    # folders
    settings.add_folder("/tmp/foo")
    settings.add_folder("/tmp/bar")
    folders = settings.get_folders()
    assert "/tmp/foo" in folders
    assert "/tmp/bar" in folders
    # remove
    settings.remove_folder("/tmp/foo")
    folders = settings.get_folders()
    assert "/tmp/foo" not in folders
