# shapes/standards/bs8666.py

import math
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass

from shapes.constants import default_standard

@dataclass
class ShapeDefinition:
    code: str
    name: str
    params: List[str]
    formula: Callable[[Dict[str, float], float], float]
    description: str

    def validate_dims(self, dims: Dict[str, Any]) -> None:
        missing = [p for p in self.params if p not in dims]
        if missing:
            raise ValueError(
                f"Shape {self.code} ({self.name}) is missing required "
                f"parameter(s): {', '.join(missing)}"
            )

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "params": self.params,
            "formula": self.formula,
            "description": self.description,
        }

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def _resolve_radius(dims: Dict[str, float], d: float) -> float:
    if "r" in dims:
        return _safe_float(dims["r"])
    return default_standard.get_bending_radius(d)

_REGISTRY: Dict[str, ShapeDefinition] = {}

def register(code: str, name: str, params: List[str],
             formula: Callable, description: str = ""):
    _REGISTRY[code] = ShapeDefinition(code, name, params, formula, description)

# ==================== BS8666 shapes ====================
register("00", "Straight", ["L"],
         lambda dims, d: _safe_float(dims["L"]))

register("11", "L-shape", ["A", "B"],
         lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"])
                          - 0.5 * _resolve_radius(dims, d) - d))

register("12", "Z-shape", ["A", "B", "C"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABC")
                          - _resolve_radius(dims, d) - 2 * d))

register("13", "Cranked both ends", ["A", "B", "C", "D"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCD")
                          - 1.5 * _resolve_radius(dims, d) - 3 * d))

register("14", "Double crank", ["A", "B", "C", "D", "E"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDE")
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("15", "Multiple crank", ["A", "B", "C", "D", "E", "F"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDEF")
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("16", "Extended crank", ["A", "B", "C", "D", "E", "F", "G"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDEFG")
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("21", "U-stirrup", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims["A"]) + _safe_float(dims["B"]))
                          - 3 * _resolve_radius(dims, d) - 4 * d))

register("22", "Open stirrup with hooks", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("23", "Open stirrup one hook", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("24", "Link with two hooks", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("25", "Full stirrup with hooks", ["A", "B", "C"],
         lambda dims, d: (2 * (_safe_float(dims["A"]) + _safe_float(dims["B"])
                               + _safe_float(dims["C"]))
                          - 4.5 * _resolve_radius(dims, d) - 9 * d))

register("26", "Stirrup with extended hooks", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("27", "Double internal stirrup", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("28", "Complex link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 3 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 5 * _resolve_radius(dims, d) - 10 * d))

register("31", "Simple helix", ["A", "B", "C", "D"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("32", "Helix with tails", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("33", "Link with crank", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 3 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("34", "Double helix", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 4.5 * _resolve_radius(dims, d) - 9 * d))

register("35", "Triangular spiral", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 3 * _safe_float(dims["B"])
                          + 3 * _safe_float(dims["C"])
                          - 5.5 * _resolve_radius(dims, d) - 11 * d))

register("36", "Rectangular spiral", ["A", "B", "C", "D"],
         lambda dims, d: (3 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 5 * _resolve_radius(dims, d) - 10 * d))

register("41", "Simple raker", ["A", "B", "C", "D", "E"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDE")
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("42", "Short raker", ["A", "B", "C", "D"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCD")
                          - 1.5 * _resolve_radius(dims, d) - 3 * d))

register("43", "Long raker", ["A", "B", "C", "D", "E", "F"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDEF")
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("44", "Double L-shape", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("45", "Asymmetric raker", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("46", "Double raker", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          - 4.5 * _resolve_radius(dims, d) - 9 * d))

register("47", "Raker with unequal legs", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("48", "Stirrup with single crank", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("51", "Open stirrup overlap", ["A", "B", "C"],
         lambda dims, d: (2 * (_safe_float(dims["A"]) + _safe_float(dims["B"]))
                          + 2 * _safe_float(dims["C"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("52", "Closed link with crank", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("53", "Stirrup with internal bend", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 3 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("54", "Double overlap link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("55", "Triple overlap link", ["A", "B", "C", "D"],
         lambda dims, d: (3 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("56", "Helical shape type 1", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("57", "Helical shape type 2", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("58", "Helical shape type 3", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("59", "Helical shape type 4", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("61", "Link with intermediate bar", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("62", "Link with two intermediates", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("63", "Link with end anchors", ["A", "B", "C", "D"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("64", "Multi-leg link", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("65", "Complex multi-leg", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("66", "Link with hooked ends", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("67", "Symmetric complex link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          - 4.5 * _resolve_radius(dims, d) - 9 * d))

register("68", "Extended multi-leg", ["A", "B", "C", "D", "E"],
         lambda dims, d: (3 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 5 * _resolve_radius(dims, d) - 10 * d))

register("70", "Stirrup with unequal legs", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("71", "Full perimeter link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("72", "Half perimeter link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("73", "Link with one hook", ["A", "B", "C", "D"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("74", "Stirrup with straight tail", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("75", "Complex stirrup with kicks", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + 2 * _safe_float(dims["D"])
                          + _safe_float(dims["E"])
                          - 4 * _resolve_radius(dims, d) - 8 * d))

register("76", "Stirrup with offset leg", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("77", "Circular hoop (lapped)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims["D"]) + d)
                          + _safe_float(dims.get("Lap", 0))))

register("78", "Circular tie (135° hooks)", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims["D"]) + d)
                          - 2 * (3 * d)
                          + 2 * default_standard.get_hook_length(d, 135)))

register("79", "Circular hoop with hooks", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims["D"]) + d)
                          + _safe_float(dims.get("Lap", 0))
                          + 2 * default_standard.get_hook_length(d, 135)))

register("81", "Straight with 90° bend at one end", ["A", "B"],
         lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"])
                          - 0.5 * _resolve_radius(dims, d) - d))

register("82", "Straight with one hook", ["A", "C"],
         lambda dims, d: (_safe_float(dims["A"])
                          + _safe_float(dims.get("C", 0))
                          + default_standard.get_hook_length(d, 90)))

register("83", "Straight with two 90° bends", ["A", "B", "C"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABC")
                          - _resolve_radius(dims, d) - 2 * d))

register("84", "Bar with two hooks", ["A"],
         lambda dims, d: (_safe_float(dims["A"])
                          + 2 * default_standard.get_hook_length(d, 90)))

register("85", "L-bar with 180° return", ["A", "B", "C"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABC")
                          - 1.5 * _resolve_radius(dims, d) - 3 * d))

register("86", "Splayed bar", ["A", "B", "C", "D"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCD")
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("87", "Staggered crank", ["A", "B", "C", "D", "E"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCDE")
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("88", "Special shape 88", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("89", "Special shape 89", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("90", "Special shape 90", ["A", "B", "C", "D"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("91", "Four-leg symmetric", ["A", "B", "C", "D"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABCD")
                          - 1.5 * _resolve_radius(dims, d) - 3 * d))

register("92", "Three-leg asymmetric", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("93", "Double asymmetric", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("94", "Link with extended leg", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 3 * _resolve_radius(dims, d) - 6 * d))

register("95", "Triple leg stirrup", ["A", "B", "C"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + 2 * _safe_float(dims["C"])
                          - 3.5 * _resolve_radius(dims, d) - 7 * d))

register("96", "Z with unequal arms", ["A", "B", "C"],
         lambda dims, d: (sum(_safe_float(dims[k]) for k in "ABC")
                          - _resolve_radius(dims, d) - 2 * d))

register("97", "Crank with one hook", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"])
                          + _safe_float(dims["C"])
                          - 2 * _resolve_radius(dims, d) - 4 * d))

register("98", "Asymmetric U-stirrup", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims["A"]) + _safe_float(dims["B"])
                          + _safe_float(dims["C"]) + _safe_float(dims["D"])
                          - 2.5 * _resolve_radius(dims, d) - 5 * d))

register("99", "Custom shape", ["TotalLength"],
         lambda dims, d: (_safe_float(dims.get("TotalLength", 0)) or
                          sum(_safe_float(v) for v in dims.values() if isinstance(v, (int, float)))))

# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def get_bs8666_shape(shape_code: str) -> Optional[dict]:
    shape = _REGISTRY.get(shape_code)
    return shape.to_dict() if shape else None

def get_all_codes() -> List[str]:
    # BS8666 codes are all numeric strings, sort by integer value
    return sorted(_REGISTRY.keys(), key=lambda x: int(x))

def get_shape_params(shape_code: str) -> List[str]:
    shape = _REGISTRY.get(shape_code)
    return shape.params if shape else []

def calculate_length(shape_code: str, dims: Dict[str, Any], d: float) -> float:
    shape = _REGISTRY.get(shape_code)
    if not shape:
        raise ValueError(f"Unknown shape code: {shape_code}")
    cleaned = {k: _safe_float(v) for k, v in dims.items()}
    shape.validate_dims(cleaned)
    return shape.formula(cleaned, d)

def list_all_shapes() -> List[Dict]:
    return [
        {"code": s.code, "name": s.name, "params": s.params, "description": s.description}
        for s in _REGISTRY.values()
    ]

BS8666_SHAPES = {code: defn.to_dict() for code, defn in _REGISTRY.items()}