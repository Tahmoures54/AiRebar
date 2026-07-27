# shapes/__init__.py
from .definitions import default_shape_registry
from .drawing import draw_shape_on_canvas

# Aliases for backward compatibility with older code that still uses these names
SHAPE_DEFINITIONS = default_shape_registry.flat_shapes

def calc_shape_length(shape_key, params, diameter_mm):
    return default_shape_registry.calc_shape_length(shape_key, params, diameter_mm)

def get_default_params(shape_key):
    return default_shape_registry.get_default_params(shape_key)

def refresh_shape_definitions():
    default_shape_registry.refresh()