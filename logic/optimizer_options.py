# logic/optimizer_options.py
"""Cutting optimizer configuration options."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class OptimizerOptions:
    scale_mm: int = 1000
    mip_time_limit: int = 12
    allow_stock_overuse: bool = True
    max_column_generation_iters: int = 30
    verbose: bool = False
    kerf_m: float = 0.0
    min_usable_scrap_m: float = 0.30
    use_multi_stock: bool = True
    strategy: str = "auto"  # auto | ffd | milp
