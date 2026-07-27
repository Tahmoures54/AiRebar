# utils/bvbs_export.py
"""
BVBS Export – AI Rebar
Generate a BVBS XML file compatible with Tekla, Revit, SOFiSTiK, Allplan, etc.
Features safe XML building, optional XSD validation, mm‑unit guarantee,
and streaming writer for large projects.
"""

import os
import json
import datetime
import logging
from typing import Optional
from db.models import RebarModel
from shapes.definitions import default_shape_registry
import config

logger = logging.getLogger(__name__)

# Mapping from BS8666 shape codes to BVBS numerical shape codes
_BS_TO_BVBS = {
    "00": "0", "01": "1", "02": "2", "03": "3",
    "11": "4", "12": "5", "13": "6", "14": "7", "15": "8",
    "21": "9", "22": "10", "23": "11", "24": "12", "25": "13",
    "26": "14", "27": "15", "28": "16", "29": "17",
    "31": "18", "32": "19", "33": "20", "34": "21", "35": "22", "36": "23",
    "41": "24", "44": "25", "46": "26", "47": "27",
    "51": "28", "52": "29", "53": "30", "54": "31", "55": "32", "56": "33",
    "61": "34", "62": "35", "63": "36", "64": "37",
    "71": "38", "72": "39", "73": "40", "74": "41", "75": "42", "77": "43",
    "81": "44", "82": "45", "98": "46", "99": "99"
}

# Threshold for switching to streaming writer (avoids large memory usage)
_STREAM_THRESHOLD = 5000


def _extract_shape_code(shape_name: str) -> str:
    """Extract the short BS8666 code from a full shape name."""
    if not shape_name:
        return ""
    s = str(shape_name).strip()
    return s.split(" - ")[0].strip() if " - " in s else s


def _get_bvbs_shape_code(bs_code: str) -> str:
    """Map a BS8666 shape code to the numerical BVBS shape code."""
    return _BS_TO_BVBS.get(bs_code, "0")


def _validate_bvbs_xml(filepath: str):
    """Optional validation using an XSD schema (if xmlschema is installed)."""
    try:
        import xmlschema
        schema_path = os.path.join(os.path.dirname(__file__), "bvbs_schema.xsd")
        if os.path.exists(schema_path):
            schema = xmlschema.XMLSchema(schema_path)
            if not schema.is_valid(filepath):
                raise ValueError("BVBS file does not comply with the XSD schema.")
            logger.info("XSD validation passed.")
    except ImportError:
        logger.debug("xmlschema not installed, skipping XSD validation.")
    except Exception as e:
        logger.warning("XSD validation error: %s", e)


def export_bvbs(
    project_id: int,
    project_name: str,
    client_name: str,
    filepath: str,
    validate_xsd: bool = False
) -> bool:
    """
    Generate a BVBS XML file for the given project.

    If the number of rebars exceeds a threshold, a streaming writer is used
    to keep memory usage low.  Optionally validates the output against an XSD.

    Returns True if data was written, False if no rebars found.
    """
    rebars = RebarModel.get_for_project(project_id)
    if not rebars:
        logger.info("No rebars found for project %s, skipping BVBS export.", project_id)
        return False

    use_stream = len(rebars) > _STREAM_THRESHOLD
    if use_stream:
        logger.info("Using streaming writer for %d rebars.", len(rebars))
        _write_bvbs_stream(filepath, project_name, client_name, rebars)
    else:
        _write_bvbs_in_memory(filepath, project_name, client_name, rebars)

    if validate_xsd:
        _validate_bvbs_xml(filepath)

    logger.info("BVBS export successful: %d rebars written to %s", len(rebars), filepath)
    return True


# ----------------------------------------------------------------------
# In‑memory builder (ElementTree)
# ----------------------------------------------------------------------
def _write_bvbs_in_memory(filepath: str, project_name: str, client_name: str, rebars):
    import xml.etree.ElementTree as ET

    root = ET.Element("bvbs", {"xmlns": "http://www.bvbs.de", "version": "1.0"})

    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "Project").text = project_name
    ET.SubElement(header, "Client").text = client_name or ""
    ET.SubElement(header, "Date").text = datetime.datetime.now().isoformat()

    bars_elem = ET.SubElement(root, "Bars")
    _populate_bars(bars_elem, rebars)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(filepath, encoding="utf-8", xml_declaration=True)


# ----------------------------------------------------------------------
# Streaming writer (low memory)
# ----------------------------------------------------------------------
def _write_bvbs_stream(filepath: str, project_name: str, client_name: str, rebars):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<bvbs xmlns="http://www.bvbs.de" version="1.0">\n')
        f.write('  <Header>\n')
        f.write(f'    <Project>{_escape_xml(project_name)}</Project>\n')
        f.write(f'    <Client>{_escape_xml(client_name or "")}</Client>\n')
        f.write(f'    <Date>{datetime.datetime.now().isoformat()}</Date>\n')
        f.write('  </Header>\n')
        f.write('  <Bars>\n')

        for r in rebars:
            bar_xml = _build_bar_xml_string(r)
            f.write(bar_xml)

        f.write('  </Bars>\n')
        f.write('</bvbs>\n')


# ----------------------------------------------------------------------
# Shared bar building logic
# ----------------------------------------------------------------------
def _populate_bars(parent_elem, rebars):
    """Append <Bar> elements to *parent_elem* (used by ElementTree builder)."""
    import xml.etree.ElementTree as ET
    for r in rebars:
        data = _extract_bar_data(r)
        if data is None:
            continue
        bar_elem = ET.SubElement(parent_elem, "Bar")
        _fill_bar_element(bar_elem, data)


def _build_bar_xml_string(r) -> str:
    """Return a <Bar> element as a formatted XML string (used by streaming writer)."""
    data = _extract_bar_data(r)
    if data is None:
        return ""
    lines = ["    <Bar>"]
    lines.append(f'      <ID>{data["id"]}</ID>')
    lines.append(f'      <Diameter>{data["dia"]}</Diameter>')
    lines.append(f'      <Quantity>{data["qty"]}</Quantity>')
    lines.append(f'      <Length>{data["length"]:.0f}</Length>')
    lines.append(f'      <ShapeCode>{data["bvbs_shape"]}</ShapeCode>')
    lines.append(f'      <Grade>{_escape_xml(data["grade"])}</Grade>')
    lines.append(f'      <Listofer>{_escape_xml(data["listofer"])}</Listofer>')
    lines.append(f'      <Position>{_escape_xml(data["pos"])}</Position>')
    for k, v in data["params"].items():
        lines.append(f'      <Param name="{_escape_xml(k)}">{v:.0f}</Param>')
    lines.append("    </Bar>")
    return "\n".join(lines) + "\n"


def _fill_bar_element(bar_elem, data):
    """Populate an ElementTree <Bar> element."""
    import xml.etree.ElementTree as ET
    ET.SubElement(bar_elem, "ID").text = str(data["id"])
    ET.SubElement(bar_elem, "Diameter").text = str(data["dia"])
    ET.SubElement(bar_elem, "Quantity").text = str(data["qty"])
    ET.SubElement(bar_elem, "Length").text = f'{data["length"]:.0f}'
    ET.SubElement(bar_elem, "ShapeCode").text = data["bvbs_shape"]
    ET.SubElement(bar_elem, "Grade").text = data["grade"]
    ET.SubElement(bar_elem, "Listofer").text = data["listofer"]
    ET.SubElement(bar_elem, "Position").text = data["pos"]
    for k, v in data["params"].items():
        param_elem = ET.SubElement(bar_elem, "Param", name=k)
        param_elem.text = f"{v:.0f}"


def _extract_bar_data(r) -> Optional[dict]:
    """Convert a raw rebar tuple into a dictionary suitable for BVBS export.
    Returns None if the record is invalid.
    """
    if len(r) < 8:
        return None
    rebar_id = r[0]
    listofer_no = r[1] or ""
    pos = r[3] or ""
    dia = r[4]
    shape_name = r[5]
    dims_str = r[6] or "{}"
    qty = r[7] or 1
    grade = r[12] if len(r) > 12 and r[12] is not None else config.DEFAULT_REBAR_GRADE

    # Parse dimensions
    try:
        dims = json.loads(dims_str) if isinstance(dims_str, str) else dims_str
        if not isinstance(dims, dict):
            dims = {}
    except Exception:
        dims = {}

    # Calculate cut length in mm using the unified shape registry
    try:
        length_mm = default_shape_registry.calc_shape_length(shape_name, dims, dia)
    except Exception:
        logger.warning("Could not calculate length for rebar %d, shape '%s'", rebar_id, shape_name)
        length_mm = 0.0

    # Map shape code
    shape_code = _extract_shape_code(shape_name)
    bvbs_shape = _get_bvbs_shape_code(shape_code)

    # Ensure all dimension values are clean integers (mm)
    clean_dims = {}
    for k, v in dims.items():
        try:
            clean_dims[k] = round(float(v))
        except (ValueError, TypeError):
            clean_dims[k] = 0

    return {
        "id": rebar_id,
        "dia": dia,
        "qty": qty,
        "length": round(length_mm),
        "bvbs_shape": bvbs_shape,
        "grade": str(grade),
        "listofer": str(listofer_no),
        "pos": str(pos),
        "params": clean_dims,
    }


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")