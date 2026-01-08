"""Tests for StatsTab and related chart widgets."""
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def app():
    """Create QApplication for testing."""
    from PySide6.QtWidgets import QApplication
    
    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(sys.argv)
    yield _app


@pytest.fixture
def db_setup(tmp_path):
    """Set up temporary database for testing."""
    from app import settings
    from app import stats_db
    
    db_path = str(tmp_path / "test_stats.db")
    settings.init_db(db_path)
    stats_db.init_stats_tables()
    yield db_path


class TestFormatDateDisplay:
    """Test format_date_display utility function."""
    
    def test_format_date_full(self):
        """Test full date formatting."""
        from app.stats_tab import format_date_display
        
        result = format_date_display("2025-12-30")
        
        assert "30" in result
        assert "Dec" in result
        assert "2025" in result
    
    def test_format_date_short(self):
        """Test short date formatting."""
        from app.stats_tab import format_date_display
        
        result = format_date_display("2025-12-30", short=True)
        
        assert "30" in result
        assert "Dec" in result
        # Short format should NOT have year
        assert "2025" not in result
    
    def test_format_date_invalid(self):
        """Test invalid date returns original string."""
        from app.stats_tab import format_date_display
        
        result = format_date_display("invalid-date")
        
        assert result == "invalid-date"
    
    def test_format_date_with_time(self):
        """Test date with time component."""
        from app.stats_tab import format_date_display
        
        result = format_date_display("2025-06-15 14:30:00")
        
        assert "15" in result
        assert "Jun" in result


class TestGetThemeColors:
    """Test get_theme_colors function."""
    
    def test_returns_dict(self, app, db_setup):
        """Test that get_theme_colors returns a dict."""
        from app.stats_tab import get_theme_colors
        
        colors = get_theme_colors()
        
        assert isinstance(colors, dict)
    
    def test_has_required_keys(self, app, db_setup):
        """Test that all required color keys are present."""
        from app.stats_tab import get_theme_colors
        
        colors = get_theme_colors()
        
        required_keys = [
            "bg_primary", "bg_secondary", "bg_tertiary",
            "text_primary", "text_secondary", "text_disabled",
            "border", "accent", "success", "warning", "error", "info"
        ]
        
        for key in required_keys:
            assert key in colors
    
    def test_colors_are_qcolor(self, app, db_setup):
        """Test that returned values are QColor objects."""
        from app.stats_tab import get_theme_colors
        from PySide6.QtGui import QColor
        
        colors = get_theme_colors()
        
        for key, value in colors.items():
            assert isinstance(value, QColor)


class TestLanguageFilterChip:
    """Test LanguageFilterChip widget."""
    
    def test_chip_initialization(self, app, db_setup):
        """Test LanguageFilterChip initializes correctly."""
        from app.stats_tab import LanguageFilterChip
        
        chip = LanguageFilterChip("Python")
        
        assert chip.language == "Python"
        assert chip.is_all is False
    
    def test_chip_all_language(self, app, db_setup):
        """Test LanguageFilterChip for 'All' option."""
        from app.stats_tab import LanguageFilterChip
        
        chip = LanguageFilterChip("All", is_all=True)
        
        assert chip.language == "All"
        assert chip.is_all is True
        assert chip._selected is True  # "All" starts selected
    
    def test_chip_selection_property(self, app, db_setup):
        """Test chip selected property."""
        from app.stats_tab import LanguageFilterChip
        
        chip = LanguageFilterChip("JavaScript")
        
        assert chip._selected is False
        
        # Set via property
        chip.selected = True
        assert chip._selected is True
        
        chip.selected = False
        assert chip._selected is False
    
    def test_chip_emits_signal(self, app, db_setup):
        """Test that clicking chip emits toggled signal."""
        from app.stats_tab import LanguageFilterChip
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        
        chip = LanguageFilterChip("Rust")
        
        signals_received = []
        chip.toggled.connect(lambda lang, sel, ctrl: signals_received.append((lang, sel, ctrl)))
        
        QTest.mouseClick(chip, Qt.LeftButton)
        
        assert len(signals_received) == 1
        assert signals_received[0][0] == "Rust"


class TestLanguageFilterBar:
    """Test LanguageFilterBar widget."""
    
    def test_filter_bar_initialization(self, app, db_setup):
        """Test LanguageFilterBar initializes correctly."""
        from app.stats_tab import LanguageFilterBar
        
        bar = LanguageFilterBar()
        
        assert bar is not None
        assert hasattr(bar, '_chips')
    
    def test_set_languages(self, app, db_setup):
        """Test setting available languages."""
        from app.stats_tab import LanguageFilterBar
        
        bar = LanguageFilterBar()
        bar.set_languages(["Python", "JavaScript", "Go"])
        
        # _chips only contains the language chips (not "All")
        assert len(bar._chips) == 3
    
    def test_get_selected_languages_default(self, app, db_setup):
        """Test get_selected_languages default is empty set."""
        from app.stats_tab import LanguageFilterBar
        
        bar = LanguageFilterBar()
        bar.set_languages(["Python", "JavaScript"])
        
        # Initially no specific language selected (empty = all)
        selected = bar.get_selected_languages()
        
        assert isinstance(selected, set)
        assert len(selected) == 0  # Empty means "all"


class TestSummaryStatCard:
    """Test SummaryStatCard widget."""
    
    def test_card_initialization(self, app, db_setup):
        """Test SummaryStatCard initializes correctly."""
        from app.stats_tab import SummaryStatCard
        
        card = SummaryStatCard("Total Sessions", "150")
        
        assert card is not None
    
    def test_card_set_value(self, app, db_setup):
        """Test updating card value."""
        from app.stats_tab import SummaryStatCard
        
        card = SummaryStatCard("Average WPM", "0")
        card.set_value("75.5")
        
        # Value should be updated
        assert "75.5" in card.value_label.text()


class TestWPMDistributionChart:
    """Test WPMDistributionChart widget."""
    
    def test_chart_initialization(self, app, db_setup):
        """Test WPMDistributionChart initializes correctly."""
        from app.stats_tab import WPMDistributionChart
        
        chart = WPMDistributionChart()
        
        assert chart is not None
        assert chart.data == []
    
    def test_chart_set_data(self, app, db_setup):
        """Test setting chart data."""
        from app.stats_tab import WPMDistributionChart
        
        chart = WPMDistributionChart()
        data = [
            {"range_label": "0-20", "count": 5},
            {"range_label": "20-40", "count": 15},
            {"range_label": "40-60", "count": 25},
        ]
        
        chart.set_data(data)
        
        assert chart.data == data
        assert len(chart.data) == 3
    
    def test_chart_rect_calculation(self, app, db_setup):
        """Test chart area calculation."""
        from app.stats_tab import WPMDistributionChart
        
        chart = WPMDistributionChart()
        chart.setFixedSize(400, 300)
        
        rect = chart._chart_rect()
        
        assert rect.width() > 0
        assert rect.height() > 0
        assert rect.left() == chart.margin_left
    
    def test_chart_apply_theme(self, app, db_setup):
        """Test applying theme colors."""
        from app.stats_tab import WPMDistributionChart
        
        chart = WPMDistributionChart()
        
        # Should not raise
        chart.apply_theme()


class TestCalendarHeatmap:
    """Test CalendarHeatmap widget."""
    
    def test_heatmap_initialization(self, app, db_setup):
        """Test CalendarHeatmap initializes correctly."""
        from app.stats_tab import CalendarHeatmap
        
        heatmap = CalendarHeatmap()
        
        assert heatmap is not None
    
    def test_heatmap_set_data(self, app, db_setup):
        """Test setting heatmap data with correct format."""
        from app.stats_tab import CalendarHeatmap
        
        heatmap = CalendarHeatmap()
        
        # Data should be a list of dicts with 'date' key
        data = [
            {"date": "2025-01-01", "count": 5, "avg_wpm": 70.0},
            {"date": "2025-01-02", "count": 3, "avg_wpm": 75.0},
        ]
        
        heatmap.set_data(data)
        
        # Data is stored in _daily_data internally
        assert heatmap._daily_data is not None
        assert len(heatmap._daily_data) == 2
    
    def test_heatmap_apply_theme(self, app, db_setup):
        """Test applying theme colors."""
        from app.stats_tab import CalendarHeatmap
        
        heatmap = CalendarHeatmap()
        
        # Should not raise
        heatmap.apply_theme()


class TestStatsTab:
    """Test main StatsTab widget."""
    
    def test_stats_tab_initialization(self, app, db_setup):
        """Test StatsTab initializes correctly."""
        from app.stats_tab import StatsTab
        
        tab = StatsTab()
        
        assert tab is not None
    
    def test_stats_tab_has_filter_bar(self, app, db_setup):
        """Test that StatsTab has language filter bar."""
        from app.stats_tab import StatsTab
        
        tab = StatsTab()
        
        assert hasattr(tab, 'filter_bar')
    
    def test_stats_tab_has_charts(self, app, db_setup):
        """Test that StatsTab has chart widgets."""
        from app.stats_tab import StatsTab
        
        tab = StatsTab()
        
        # Should have various chart components
        assert hasattr(tab, 'wpm_distribution_chart')
        assert hasattr(tab, 'calendar_heatmap')
    
    def test_stats_tab_refresh(self, app, db_setup):
        """Test refreshing stats data."""
        from app.stats_tab import StatsTab
        
        tab = StatsTab()
        
        # Should not raise - method is refresh(), not refresh_stats()
        tab.refresh()
    
    def test_stats_tab_apply_theme(self, app, db_setup):
        """Test applying theme to all components."""
        from app.stats_tab import StatsTab
        
        tab = StatsTab()
        
        # Should not raise
        tab.apply_theme()
