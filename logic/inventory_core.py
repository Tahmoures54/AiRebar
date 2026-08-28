# logic/inventory_core.py
"""Stock/scrap InventoryManager and row parsing."""
from __future__ import annotations

from typing import List, Optional, Tuple

from db.models import ScrapModel, StockModel
from config import STANDARD_STOCK_LENGTHS_M, DEFAULT_REBAR_GRADE
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.Inventory")


def _parse_stock_row(row) -> Optional[Tuple[float, int, int]]:
    if not row or len(row) < 4:
        return None
    stock_id = row[0]
    if len(row) >= 6:
        length_mm, qty = row[3], row[4]
    else:
        length_mm, qty = row[2], row[3]
    try:
        return int(stock_id), float(length_mm), int(qty)
    except Exception:
        return None


class InventoryManager:
    def __init__(self, project_id: int, stock_lengths_m: Optional[List[float]] = None):
        self.project_id = project_id
        self.stock_lengths_m = stock_lengths_m or STANDARD_STOCK_LENGTHS_M

    def get_stock_bars(self, diameter: float, grade: str = DEFAULT_REBAR_GRADE) -> List[Tuple[float, int]]:
        try:
            rows = StockModel.get_for_diameter(self.project_id, diameter, grade)
            result = []
            for r in rows:
                parsed = _parse_stock_row(r)
                if not parsed:
                    continue
                _, length_mm, qty = parsed
                if qty > 0:
                    result.append((length_mm, qty))
            return result
        except Exception as e:
            logger.error(f"Failed to fetch stock bars: {e}")
            return []

    def add_stock_bar(self, diameter: float, length_mm: float, quantity: int = 1,
                      grade: str = DEFAULT_REBAR_GRADE) -> Optional[int]:
        try:
            stock_id = StockModel.add_stock(self.project_id, diameter, length_mm, quantity, grade)
            return stock_id
        except Exception as e:
            logger.error(f"Failed to add stock bar: {e}")
            return None

    def consume_stock_bar(self, diameter: float, length_mm: float, quantity: int = 1,
                          grade: str = DEFAULT_REBAR_GRADE) -> bool:
        try:
            rows = StockModel.get_for_diameter(self.project_id, diameter, grade)
            for r in rows:
                parsed = _parse_stock_row(r)
                if not parsed:
                    continue
                stock_id, L, qty = parsed
                if abs(L - float(length_mm)) < 1e-6:
                    if qty >= quantity:
                        StockModel.update_quantity(stock_id, qty - quantity)
                        return True
                    return False
            return False
        except Exception as e:
            logger.error(f"Failed to consume stock bar: {e}")
            return False

    def get_available_stock_lengths_mm(self, diameter: float, grade: str = DEFAULT_REBAR_GRADE) -> List[float]:
        stock_items = self.get_stock_bars(diameter, grade)
        if stock_items:
            return [length for length, qty in stock_items if qty > 0]
        return [l * 1000 for l in self.stock_lengths_m]

    def get_scraps(self, diameter: float, grade: Optional[str] = None) -> List[float]:
        try:
            scraps = ScrapModel.get_available_scraps(self.project_id, diameter, grade=grade)
            return [float(s[1]) for s in scraps if len(s) >= 2]
        except Exception as e:
            logger.error(f"Failed to fetch scraps: {e}")
            return []

    def add_scrap(self, diameter: float, length_mm: float, grade: Optional[str] = None,
                  listofer_number: Optional[str] = None) -> Optional[int]:
        grade = grade or DEFAULT_REBAR_GRADE
        try:
            return ScrapModel.add_scrap(self.project_id, diameter, length_mm, grade=grade,
                                        listofer_number=listofer_number)
        except Exception as e:
            logger.error(f"Failed to add scrap: {e}")
            return None

    def mark_scrap_used(self, scrap_id: int) -> bool:
        try:
            ScrapModel.mark_as_used(scrap_id)
            return True
        except Exception as e:
            logger.error(f"Failed to mark scrap as used: {e}")
            return False

    def delete_scrap(self, scrap_id: int) -> bool:
        try:
            ScrapModel.delete_scrap(scrap_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete scrap: {e}")
            return False

    def get_all_scraps(self, diameter: Optional[float] = None, grade: Optional[str] = None):
        try:
            return ScrapModel.get_all_scraps(self.project_id, diameter=diameter, grade=grade)
        except Exception as e:
            logger.error(f"Failed to fetch all scraps: {e}")
            return []
