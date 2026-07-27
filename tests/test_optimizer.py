# tests/test_optimizer.py
import pytest
from collections import Counter

import logic.optimizer as opt
from logic.optimizer import optimize_cuts, optimize_labeled_cuts

TOL = 1e-6


def _flatten(bins):
    return [float(x) for b in bins for x in b]


def _counter(vals):
    return Counter(round(float(v), 6) for v in vals)


def _assert_feasible(bins, stock_length):
    for b in bins:
        assert sum(b) <= stock_length + TOL


def _expected_new_scraps(plans, stock_length):
    """
    new_scraps are created only from stock bars (scrap_id == None).
    """
    scraps = []
    for p in plans:
        if p.get("scrap_id") is None and abs(float(p.get("bar_length", 0)) - float(stock_length)) <= TOL:
            used = sum(float(l) for l, _ in p.get("bin", []))
            waste = float(stock_length) - used
            if waste > TOL:
                scraps.append(waste)
    return sorted(scraps)


class TestOptimizeCuts:
    """Unit: metres"""

    def test_single_piece_fits_stock(self):
        bins = optimize_cuts([3.0], 12.0)
        assert _counter(_flatten(bins)) == _counter([3.0])
        _assert_feasible(bins, 12.0)

    def test_exact_multiple_fit_in_one_bar_when_possible(self):
        bins = optimize_cuts([4.0, 4.0, 4.0], 12.0)
        assert _counter(_flatten(bins)) == _counter([4.0, 4.0, 4.0])
        _assert_feasible(bins, 12.0)

        # Optimality check only if PuLP is available
        if opt.PULP_AVAILABLE:
            assert len(bins) == 1

    def test_pieces_require_multiple_bars(self):
        bins = optimize_cuts([8.0, 8.0], 12.0)
        assert _counter(_flatten(bins)) == _counter([8.0, 8.0])
        _assert_feasible(bins, 12.0)
        assert len(bins) >= 2

    def test_empty_lengths_returns_empty(self):
        assert optimize_cuts([], 12.0) == []

    def test_invalid_stock_returns_empty(self):
        assert optimize_cuts([1.0, 2.0], 0) == []
        assert optimize_cuts([1.0, 2.0], -10) == []

    def test_fallback_without_pulp(self, monkeypatch):
        orig = opt.PULP_AVAILABLE
        monkeypatch.setattr(opt, "PULP_AVAILABLE", False)

        bins = optimize_cuts([3.0, 5.0], 12.0)
        assert _counter(_flatten(bins)) == _counter([3.0, 5.0])
        _assert_feasible(bins, 12.0)

        monkeypatch.setattr(opt, "PULP_AVAILABLE", orig)


class TestOptimizeLabeledCuts:
    """Unit: metres"""

    def test_no_scraps_only_stock(self):
        items = [(5.0, {"pos": "1"}), (5.0, {"pos": "2"})]
        stock_length = 12.0

        plans, new_scraps = optimize_labeled_cuts(items, stock_length)

        planned = [l for p in plans for (l, _) in p["bin"]]
        assert _counter(planned) == _counter([5.0, 5.0])

        for p in plans:
            assert sum(l for l, _ in p["bin"]) <= float(p["bar_length"]) + TOL

        assert sorted(new_scraps) == pytest.approx(_expected_new_scraps(plans, stock_length))

    def test_with_available_scrap(self):
        items = [(7.0, {"pos": "A"}), (4.0, {"pos": "B"})]
        scrap_list = [8.0]
        stock_length = 12.0

        plans, new_scraps = optimize_labeled_cuts(items, stock_length, scrap_list)

        planned = [l for p in plans for (l, _) in p["bin"]]
        assert _counter(planned) == _counter([7.0, 4.0])

        bar_lengths = sorted(float(p["bar_length"]) for p in plans)
        assert 8.0 in bar_lengths  # should use scrap

        assert sorted(new_scraps) == pytest.approx(_expected_new_scraps(plans, stock_length))

    def test_empty_items(self):
        plans, new_scraps = optimize_labeled_cuts([], 12.0)
        assert plans == []
        assert new_scraps == []