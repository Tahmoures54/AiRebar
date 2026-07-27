# tests/test_calculator.py
import pytest
from config import WEIGHT_COEFFICIENT
from logic.calculator import calculate_weight, calculate_total_weight, calculate_lap_splice


class TestCalculateWeight:
    def test_10mm_1m(self):
        unit_wt, total_wt = calculate_weight(10, 1000)  # 1m
        expected_unit = (10 ** 2) * WEIGHT_COEFFICIENT
        assert unit_wt == pytest.approx(expected_unit, abs=1e-6)
        assert total_wt == pytest.approx(expected_unit, abs=1e-6)

    def test_zero_length(self):
        _, total_wt = calculate_weight(12, 0)
        assert total_wt == 0.0

    def test_positive_return_values(self):
        unit, total = calculate_weight(20, 3000)
        assert unit > 0
        assert total > 0

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            calculate_weight(0, 1000)
        with pytest.raises(ValueError):
            calculate_weight(10, -10)


class TestCalculateTotalWeight:
    def test_multiple_bars(self):
        dia = 12
        length_mm = 2000
        qty = 5
        unit_wt = (dia ** 2) * WEIGHT_COEFFICIENT
        expected = unit_wt * (length_mm / 1000.0) * qty
        assert calculate_total_weight(dia, length_mm, qty) == pytest.approx(expected, abs=1e-9)

    def test_single_bar(self):
        dia = 16
        length_mm = 1000
        _, total = calculate_weight(dia, length_mm)
        assert calculate_total_weight(dia, length_mm, 1) == pytest.approx(total, abs=1e-12)

    def test_negative_quantity_raises(self):
        with pytest.raises(ValueError):
            calculate_total_weight(10, 1000, -1)


class TestLapSplice:
    def test_basic_lap(self):
        lap = calculate_lap_splice(16, fy=500, fc=25)
        assert lap >= 300

    def test_minimum_length(self):
        lap = calculate_lap_splice(8, fy=300, fc=20)
        assert lap >= 300

    def test_requires_positive_values(self):
        with pytest.raises(ValueError):
            calculate_lap_splice(0, 500, 25)
        with pytest.raises(ValueError):
            calculate_lap_splice(12, -400, 25)
        with pytest.raises(ValueError):
            calculate_lap_splice(12, 400, 0)

    def test_large_diameter_uses_different_denom(self):
        lap_20 = calculate_lap_splice(20, fy=500, fc=25)
        lap_14 = calculate_lap_splice(14, fy=500, fc=25)
        assert lap_20 > lap_14

    def test_epoxy_coating_factor(self):
        lap_coated = calculate_lap_splice(16, fy=500, fc=25, epoxy_coated=True, epoxy_cover_sufficient=False)
        lap_normal = calculate_lap_splice(16, fy=500, fc=25)
        assert lap_coated > lap_normal

        lap_coated_suff = calculate_lap_splice(16, fy=500, fc=25, epoxy_coated=True, epoxy_cover_sufficient=True)
        assert lap_coated_suff < lap_coated
        assert lap_coated_suff > lap_normal

    def test_high_strength_fy_factor(self):
        lap_high = calculate_lap_splice(16, fy=600, fc=25)
        lap_normal = calculate_lap_splice(16, fy=500, fc=25)
        assert lap_high > lap_normal