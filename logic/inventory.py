# logic/inventory.py
"""
Inventory management for reinforcement bars:
- standard stock lengths (from config, actual stock from DB)
- available scrap pieces

Robust against different StockModel row formats.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict

from db.models import ScrapModel, StockModel
from config import STANDARD_STOCK_LENGTHS_M, DEFAULT_REBAR_GRADE
from utils.logger import setup_logger

logger = setup_logger("AI_Rebar.Inventory")


def _parse_stock_row(row) -> Optional[Tuple[float, int, int]]:
    """
    Try to parse a stock row and return (stock_id, length_mm, qty).
    Supports common layouts:
      A) (id, project_id, diameter, length_mm, qty, grade)
      B) (id, diameter, length_mm, qty, grade)
      C) (id, project_id, diameter, length_mm, qty)
      D) (id, diameter, length_mm, qty)
    """
    if not row or len(row) < 4:
        return None

    stock_id = row[0]

    length_mm = None
    qty = None

    if len(row) >= 6:
        length_mm = row[3]
        qty = row[4]
    else:
        length_mm = row[2]
        qty = row[3]

    try:
        return int(stock_id), float(length_mm), int(qty)
    except Exception:
        return None


class InventoryManager:
    """Manage full bars and scraps for a project."""

    def __init__(self, project_id: int, stock_lengths_m: Optional[List[float]] = None):
        self.project_id = project_id
        self.stock_lengths_m = stock_lengths_m or STANDARD_STOCK_LENGTHS_M

    # -----------------------------------------------------------------
    # Full stock bars (physical inventory from DB)
    # -----------------------------------------------------------------
    def get_stock_bars(self, diameter: float, grade: str = DEFAULT_REBAR_GRADE) -> List[Tuple[float, int]]:
        """
        Return available stock lengths (mm) with their remaining quantity for a given diameter and grade.
        Returns: List[(length_mm, qty)] for qty > 0
        """
        try:
            rows = StockModel.get_for_diameter(self.project_id, diameter, grade)
            result: List[Tuple[float, int]] = []
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
            logger.info(f"Stock bar added/updated: dia={diameter}mm len={length_mm}mm qty={quantity} grade={grade}")
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
                        logger.info(f"Consumed stock: id={stock_id} len={length_mm} qty={quantity}")
                        return True
                    logger.warning(f"Insufficient stock for len={length_mm}: need={quantity}, have={qty}")
                    return False

            logger.warning(f"No stock entry for len={length_mm} dia={diameter} grade={grade}")
            return False
        except Exception as e:
            logger.error(f"Failed to consume stock bar: {e}")
            return False

    def get_available_stock_lengths_mm(self, diameter: float, grade: str = DEFAULT_REBAR_GRADE) -> List[float]:
        stock_items = self.get_stock_bars(diameter, grade)
        if stock_items:
            return [length for length, qty in stock_items if qty > 0]
        return [l * 1000 for l in self.stock_lengths_m]

    # -----------------------------------------------------------------
    # Scrap management
    # -----------------------------------------------------------------
    def get_scraps(self, diameter: float, grade: Optional[str] = None) -> List[float]:
        try:
            scraps = ScrapModel.get_available_scraps(self.project_id, diameter, grade=grade)
            result = []
            for s in scraps:
                if len(s) >= 2:
                    result.append(float(s[1]))
            return result
        except Exception as e:
            logger.error(f"Failed to fetch scraps: {e}")
            return []

    def add_scrap(self, diameter: float, length_mm: float, grade: Optional[str] = None,
                  listofer_number: Optional[str] = None) -> Optional[int]:
        grade = grade or DEFAULT_REBAR_GRADE
        try:
            scrap_id = ScrapModel.add_scrap(self.project_id, diameter, length_mm, grade=grade,
                                            listofer_number=listofer_number)
            logger.info(f"Scrap added: id={scrap_id} dia={diameter} len={length_mm} grade={grade}")
            return scrap_id
        except Exception as e:
            logger.error(f"Failed to add scrap: {e}")
            return None

    def mark_scrap_used(self, scrap_id: int) -> bool:
        try:
            ScrapModel.mark_as_used(scrap_id)
            logger.info(f"Scrap {scrap_id} marked as used.")
            return True
        except Exception as e:
            logger.error(f"Failed to mark scrap as used: {e}")
            return False

    def delete_scrap(self, scrap_id: int) -> bool:
        try:
            ScrapModel.delete_scrap(scrap_id)
            logger.info(f"Scrap {scrap_id} deleted.")
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