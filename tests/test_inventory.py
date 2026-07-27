# tests/test_inventory.py
"""
Tests for the InventoryManager class.
Uses monkeypatch to isolate the database layer.
"""

import pytest
from logic.inventory import InventoryManager
from db.models import ScrapModel, StockModel
from config import DEFAULT_REBAR_GRADE


class TestInventoryManager:
    @pytest.fixture
    def manager(self, monkeypatch):
        # Ensure no real DB reads
        monkeypatch.setattr(StockModel, "get_for_diameter", lambda project_id, diameter, grade=None: [])
        return InventoryManager(project_id=99)

    def test_get_available_stock_lengths_mm(self, manager):
        # Fallback to config lengths (6m, 12m) converted to mm
        lengths = manager.get_available_stock_lengths_mm(diameter=10)
        assert lengths == [6000, 12000] or lengths == [6000.0, 12000.0]

    def test_get_scraps_empty(self, manager, monkeypatch):
        monkeypatch.setattr(ScrapModel, "get_available_scraps", lambda pid, dia, grade=None: [])
        scraps = manager.get_scraps(diameter=12)
        assert scraps == []

    def test_get_scraps_with_data(self, manager, monkeypatch):
        monkeypatch.setattr(
            ScrapModel,
            "get_available_scraps",
            lambda pid, dia, grade=None: [
                (1, 500.0, "A3", None),
                (2, 350.0, "A2", "L-001"),
            ],
        )
        scraps = manager.get_scraps(diameter=16)
        assert scraps == [500.0, 350.0]

    def test_add_scrap_calls_model(self, manager, monkeypatch):
        captured = {}

        def fake_add_scrap(pid, diameter, length_mm, grade=None, date=None, listofer_number=None):
            captured["pid"] = pid
            captured["diameter"] = diameter
            captured["length_mm"] = length_mm
            captured["grade"] = grade
            captured["listofer_number"] = listofer_number
            return 123

        monkeypatch.setattr(ScrapModel, "add_scrap", fake_add_scrap)
        result = manager.add_scrap(diameter=10, length_mm=750)

        assert result == 123
        assert captured["pid"] == 99
        assert captured["diameter"] == 10
        assert captured["length_mm"] == 750
        assert captured["grade"] == DEFAULT_REBAR_GRADE
        assert captured["listofer_number"] is None

    def test_mark_scrap_used(self, manager, monkeypatch):
        calls = []
        monkeypatch.setattr(ScrapModel, "mark_as_used", lambda scrap_id: calls.append(scrap_id))
        assert manager.mark_scrap_used(5) is True
        assert calls == [5]

    def test_delete_scrap(self, manager, monkeypatch):
        calls = []
        monkeypatch.setattr(ScrapModel, "delete_scrap", lambda scrap_id: calls.append(scrap_id))
        assert manager.delete_scrap(7) is True
        assert calls == [7]

    def test_get_all_scraps_default(self, manager, monkeypatch):
        mock_data = [
            (1, 12, 300, "A3", "2025-01-01", 0, None),
            (2, 16, 450, "A2", "2025-01-02", 1, "L-005"),
        ]
        monkeypatch.setattr(ScrapModel, "get_all_scraps", lambda pid, diameter=None, grade=None: mock_data)
        result = manager.get_all_scraps()
        assert result == mock_data
        assert len(result) == 2

    def test_get_all_scraps_with_diameter_filter(self, manager, monkeypatch):
        def fake_all(pid, diameter=None, grade=None):
            return [(3, 12, 200, "A1", "2025-02-01", 0, None)]

        monkeypatch.setattr(ScrapModel, "get_all_scraps", fake_all)
        result = manager.get_all_scraps(diameter=12)
        assert result == [(3, 12, 200, "A1", "2025-02-01", 0, None)]