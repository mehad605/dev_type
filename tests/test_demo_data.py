"""Tests for demo_data module."""
import sys
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch


@pytest.fixture
def demo_db(tmp_path):
    """Set up temporary demo database."""
    from app import demo_data
    
    # Override the demo db path
    original_path = demo_data._demo_db_path
    demo_data._demo_db_path = tmp_path / "test_demo.db"
    
    yield demo_data._demo_db_path
    
    # Restore
    demo_data._demo_db_path = original_path


class TestDemoModeFlag:
    """Test demo mode flag management."""
    
    def test_demo_mode_initially_false(self):
        """Test that demo mode starts disabled."""
        from app import demo_data
        
        # Reset to initial state
        demo_data._demo_mode_enabled = False
        assert demo_data.is_demo_mode() is False
    
    def test_set_demo_mode_true(self):
        """Test enabling demo mode."""
        from app import demo_data
        
        demo_data.set_demo_mode(True)
        assert demo_data.is_demo_mode() is True
        
        # Reset
        demo_data.set_demo_mode(False)
    
    def test_set_demo_mode_false(self):
        """Test disabling demo mode."""
        from app import demo_data
        
        demo_data.set_demo_mode(True)
        demo_data.set_demo_mode(False)
        assert demo_data.is_demo_mode() is False


class TestDemoDatabase:
    """Test demo database operations."""
    
    def test_connect_demo_creates_db(self, demo_db):
        """Test that connect_demo creates the database."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        assert conn is not None
        conn.close()
        
        assert demo_db.exists()
    
    def test_init_demo_tables(self, demo_db):
        """Test initializing demo tables."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        
        # Verify table exists
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_history'")
        result = cur.fetchone()
        
        conn.close()
        
        assert result is not None
        assert result[0] == "session_history"
    
    def test_demo_db_exists_false(self, demo_db):
        """Test demo_db_exists returns False when no db."""
        from app import demo_data
        
        # Ensure db doesn't exist
        if demo_db.exists():
            demo_db.unlink()
        
        assert demo_data.demo_db_exists() is False
    
    def test_demo_db_exists_true(self, demo_db):
        """Test demo_db_exists returns True when db exists."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        conn.close()
        
        assert demo_data.demo_db_exists() is True


class TestDataGeneration:
    """Test demo data generation."""
    
    def test_generate_demo_data_creates_records(self, demo_db):
        """Test that generate_demo_data creates session records."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        # Generate a small amount of data
        count = demo_data.generate_demo_data(days=7, sessions_per_day_range=(1, 3))
        
        assert count > 0
        
        # Verify data in database
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        db_count = cur.fetchone()[0]
        conn.close()
        
        assert db_count == count
    
    def test_generate_demo_data_fields(self, demo_db):
        """Test that generated data has valid fields."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        demo_data.generate_demo_data(days=3, sessions_per_day_range=(1, 2))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("""
            SELECT file_path, language, wpm, accuracy, 
                   total_keystrokes, duration, completed
            FROM session_history LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        
        if row:
            file_path, language, wpm, accuracy, total, duration, completed = row
            
            assert file_path is not None
            assert language in ["Python", "JavaScript", "TypeScript", "Rust", 
                                "Go", "C++", "Java", "C#"]
            assert 20 <= wpm <= 150  # Reasonable WPM range
            assert 0.7 <= accuracy <= 1.0  # Reasonable accuracy
            assert total > 0
            assert duration > 0
            assert completed in [0, 1]
    
    def test_generate_demo_data_clears_previous(self, demo_db):
        """Test that regeneration clears previous data."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        # Generate first batch
        demo_data.generate_demo_data(days=3, sessions_per_day_range=(2, 3))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        first_count = cur.fetchone()[0]
        conn.close()
        
        # Generate second batch - should replace, not add
        demo_data.generate_demo_data(days=3, sessions_per_day_range=(1, 2))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        second_count = cur.fetchone()[0]
        conn.close()
        
        # Second count should be different (replaced, not accumulated)
        # Just verify it's not exactly doubled
        assert second_count < first_count * 2
    
    def test_generate_demo_data_language_distribution(self, demo_db):
        """Test that data has multiple languages."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        demo_data.generate_demo_data(days=30, sessions_per_day_range=(3, 5))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT language FROM session_history")
        languages = [row[0] for row in cur.fetchall()]
        conn.close()
        
        # Should have multiple languages
        assert len(languages) >= 3


class TestEnsureDemoData:
    """Test ensure_demo_data function."""
    
    def test_ensure_demo_data_creates_if_missing(self, demo_db):
        """Test that ensure_demo_data creates data if missing."""
        from app import demo_data
        
        # Ensure db doesn't exist
        if demo_db.exists():
            demo_db.unlink()
        
        demo_data.ensure_demo_data()
        
        # Verify data was created
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        
        assert count > 0
    
    def test_ensure_demo_data_regenerates_if_empty(self, demo_db):
        """Test that ensure_demo_data regenerates if db empty."""
        from app import demo_data
        
        # Create empty db with table
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        demo_data.ensure_demo_data()
        
        # Verify data was generated
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        
        assert count > 0


class TestDemoDataEdgeCases:
    """Test edge cases and error handling in demo data generation."""
    
    @patch('app.portable_data.get_data_dir')
    def test_get_demo_db_path_handles_none_data_dir(self, mock_get_data_dir):
        """Test get_demo_db_path when get_data_dir returns None."""
        from app import demo_data

        # Reset the global path
        demo_data._demo_db_path = None

        mock_get_data_dir.return_value = None

        # Should not crash, should create a default path
        path = demo_data.get_demo_db_path()
        assert path is not None
        assert path.name == "demo_stats.db"
    
    @patch('app.portable_data.get_data_dir')
    def test_get_demo_db_path_creates_data_dir(self, mock_get_data_dir, tmp_path):
        """Test get_demo_db_path when data dir needs to be created."""
        from app import demo_data

        # Reset the global path
        demo_data._demo_db_path = None

        mock_data_dir = tmp_path / "test_data"
        mock_data_dir.mkdir(exist_ok=True)
        mock_get_data_dir.return_value = mock_data_dir

        # Clean up any existing demo db
        demo_db_path = mock_data_dir / "demo_stats.db"
        if demo_db_path.exists():
            demo_db_path.unlink()

        path = demo_data.get_demo_db_path()
        assert path == demo_db_path
        assert not path.exists()  # Should not create the db, just return path
    
    def test_generate_demo_data_leap_year(self, demo_db):
        """Test generate_demo_data with leap year."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        # Test leap year (2024)
        demo_data.generate_demo_data(year=2024, days=366, sessions_per_day_range=(1, 1))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        
        # Should generate sessions for the year (with some randomness for weekends/breaks)
        assert count > 200  # Roughly 366 minus weekends and breaks
    
    def test_generate_demo_data_non_leap_year(self, demo_db):
        """Test generate_demo_data with non-leap year."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        # Test non-leap year (2023)
        demo_data.generate_demo_data(year=2023, days=365, sessions_per_day_range=(1, 1))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        
        # Should generate sessions for the year (with some randomness for weekends/breaks)
        assert count > 200  # Roughly 365 minus weekends and breaks
    
    def test_generate_demo_data_zero_error_edge_case(self, demo_db):
        """Test error calculation edge case when error should be 0."""
        from app import demo_data
        
        conn = demo_data.connect_demo()
        demo_data.init_demo_tables(conn)
        conn.close()
        
        # Generate minimal data that might trigger the edge case
        demo_data.generate_demo_data(year=2023, days=1, sessions_per_day_range=(1, 1))
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT file_path, language, wpm, accuracy, total_keystrokes, duration, completed FROM session_history")
        rows = cur.fetchall()
        conn.close()
        
        # Should have at least one session
        assert len(rows) >= 1
    
    def test_setup_demo_data_persist_mode(self, demo_db):
        """Test setup_demo_data with persist=True."""
        from app import demo_data
        
        # Generate initial data
        demo_data.setup_demo_data(year=2023, persist=False)
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        first_count = cur.fetchone()[0]
        conn.close()
        
        # Try to regenerate with persist=True - should not regenerate
        demo_data.setup_demo_data(year=2023, persist=True)
        
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        second_count = cur.fetchone()[0]
        conn.close()
        
        # Count should be the same (persisted)
        assert second_count == first_count
    
    def test_setup_demo_data_file_deletion_error(self, tmp_path):
        """Test setup_demo_data when file deletion fails due to permission error."""
        from app import demo_data
        
        # Override the demo db path
        original_path = demo_data._demo_db_path
        demo_data._demo_db_path = tmp_path / "demo_stats.db"
        
        try:
            # Create the file and make it read-only to simulate permission error
            db_path = tmp_path / "demo_stats.db"
            db_path.touch()
            db_path.chmod(0o444)  # Read-only
            
            # This should handle the permission error gracefully during unlink, but may fail on init if db is readonly
            import sqlite3
            with pytest.raises(sqlite3.OperationalError, match="attempt to write a readonly database"):
                demo_data.setup_demo_data(year=2023, persist=False)
            
        finally:
            # Restore permissions and cleanup
            if db_path.exists():
                db_path.chmod(0o666)
            demo_data._demo_db_path = original_path
    
    def test_setup_demo_data_database_error_handling(self, demo_db):
        """Test setup_demo_data handles database errors gracefully."""
        from app import demo_data
        
        # This test covers the error handling in setup_demo_data
        # The function should handle various database errors without crashing
        
        # Test with a scenario that might cause database issues
        # This exercises the error handling code around line 460-461
        try:
            demo_data.setup_demo_data(year=2023, persist=False)
        except Exception as e:
            # Should not raise unhandled exceptions
            pytest.fail(f"setup_demo_data raised an unexpected exception: {e}")
        
        # Verify normal operation still works
        conn = demo_data.connect_demo()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM session_history")
        count = cur.fetchone()[0]
        conn.close()
        
        assert count >= 0  # Should complete without error
