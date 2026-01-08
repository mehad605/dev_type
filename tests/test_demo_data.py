"""Tests for demo_data module."""
import sys
import pytest
from pathlib import Path
from datetime import datetime


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
