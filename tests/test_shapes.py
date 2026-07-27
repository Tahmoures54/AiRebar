# tests/test_shapes.py
from shapes.definitions import default_shape_registry


def test_shapes_registry_loads():
    assert len(default_shape_registry.flat_shapes) > 0


def test_each_shape_has_min_contract():
    required = {"code", "params", "calc_length", "draw_func", "standard_code"}
    for key, s in default_shape_registry.flat_shapes.items():
        assert isinstance(s, dict)
        assert required.issubset(set(s.keys()))
        assert isinstance(s["params"], list)
        assert callable(s["calc_length"])