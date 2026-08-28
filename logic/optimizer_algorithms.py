# logic/optimizer_algorithms.py
"""Algorithms facade: CG + MIP + labeled."""
from __future__ import annotations
from logic.optimizer_cg import optimize_cuts
from logic.optimizer_mip import optimize_cuts_mip_indexed, optimize_labeled_cuts

__all__ = ["optimize_cuts", "optimize_cuts_mip_indexed", "optimize_labeled_cuts"]
