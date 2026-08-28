# utils/doctor.py
"""System Doctor – pre-release / runtime health checks for RebarAgent."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from utils.logger import setup_logger

logger = setup_logger("RebarAgent.Doctor")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    level: str = "info"


@dataclass
class DoctorReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any((not c.ok and c.level == "error") for c in self.checks)

    @property
    def errors(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.ok and c.level == "error"]

    def as_text(self) -> str:
        lines = ["RebarAgent System Doctor", "=" * 40]
        for c in self.checks:
            if c.ok:
                mark = "OK"
            elif c.level == "warning":
                mark = "WARN"
            else:
                mark = "FAIL"
            lines.append(f"[{mark}] {c.name}: {c.detail}")
        lines.append("=" * 40)
        lines.append("PASS" if self.ok else "FAIL — fix errors before release")
        return "\n".join(lines)


def _check(name: str, fn: Callable[[], str], level_on_fail: str = "error") -> CheckResult:
    try:
        detail = fn() or "ok"
        return CheckResult(name=name, ok=True, detail=detail, level="info")
    except Exception as e:
        logger.error("Doctor check '%s' failed: %s", name, e)
        return CheckResult(name=name, ok=False, detail=str(e), level=level_on_fail)


def run_doctor(project_id: Optional[int] = None) -> DoctorReport:
    report = DoctorReport()
    report.checks.append(_check("python", lambda: f"{sys.version.split()[0]} ({sys.platform})"))

    def _imports():
        from db.database import db  # noqa: F401
        from shapes.definitions import default_shape_registry  # noqa: F401
        bits = ["db", "shapes"]
        try:
            import tkinter  # noqa: F401
            bits.append("tkinter")
        except Exception:
            bits.append("tkinter:missing(headless)")
        return ", ".join(bits)

    report.checks.append(_check("core_imports", _imports))

    def _schema():
        from db.database import db
        from db.migrations import SCHEMA_VERSION, get_schema_version
        ver = getattr(db, "schema_version", None)
        if ver is None:
            try:
                ver = get_schema_version(db.connection)
            except Exception as e:
                return f"unreadable ({e})"
        ver = int(ver or 0)
        if ver < SCHEMA_VERSION:
            raise RuntimeError(f"schema_version={ver} < expected {SCHEMA_VERSION}")
        return f"schema_version={ver}"

    report.checks.append(_check("database_schema", _schema, level_on_fail="warning"))

    def _shapes():
        from shapes.definitions import default_shape_registry
        reg = default_shape_registry
        reg.refresh()
        hr = reg.health_report()
        empty = hr.get("empty_standards") or []
        if empty:
            raise RuntimeError(f"empty standards: {empty}")
        if hr.get("missing_calc_length"):
            raise RuntimeError(f"shapes missing calc_length: {len(hr['missing_calc_length'])}")
        ir_n = hr.get("by_standard", {}).get("ir", 0)
        if ir_n <= 0:
            raise RuntimeError("Iran (Mabhas 9) shapes not loaded")
        return f"total={hr['total_shapes']} ir={ir_n}"

    report.checks.append(_check("shape_registry", _shapes))

    def _length():
        from shapes.definitions import default_shape_registry
        reg = default_shape_registry
        keys = reg.get_shape_keys_by_standard("bs") or list(reg.flat_shapes.keys())
        if not keys:
            raise RuntimeError("no shapes")
        k = keys[0]
        L = reg.calc_shape_length(k, reg.get_default_params(k), 12.0)
        if L <= 0:
            raise RuntimeError(f"non-positive length for {k}")
        return f"{k} → {L:.1f} mm"

    report.checks.append(_check("length_calc", _length))

    def _validation():
        from logic.validation import validate_position, summarize
        issues = validate_position("00 - Straight", {"L": 1000}, 12, 2, "bs")
        err, warn, _ = summarize(issues)
        if err:
            raise RuntimeError("unexpected errors on valid bar")
        bad = validate_position("", {}, 0, 0)
        if not any(i.level == "error" for i in bad):
            raise RuntimeError("expected errors for empty position")
        return f"ok (sample warnings={warn})"

    report.checks.append(_check("validation", _validation))

    def _events():
        from utils.events import EventBus
        b = EventBus()
        seen = []
        b.subscribe("test.ping", lambda p: seen.append(p.get("x")))
        b.emit("test.ping", {"x": 1})
        if seen != [1]:
            raise RuntimeError("event not delivered")
        return "bus ok"

    report.checks.append(_check("event_bus", _events))

    def _backup_api():
        from utils import project_backup as pb
        assert callable(getattr(pb, "backup_full_database", None))
        assert callable(getattr(pb, "export_project_json", None))
        return "backup_full_database + export_project_json"

    report.checks.append(_check("backup_api", _backup_api, level_on_fail="warning"))

    if project_id is not None:
        def _project():
            from db.models import RebarModel
            from logic.validation import validate_project_positions, summarize
            rows = RebarModel.get_for_project(project_id) or []
            issues = validate_project_positions(rows)
            err, warn, _ = summarize(issues)
            if err:
                raise RuntimeError(f"{err} error(s) in project positions")
            return f"positions={len(rows)} warnings={warn}"
        report.checks.append(_check("project_positions", _project, level_on_fail="warning"))

    logger.info("Doctor finished ok=%s errors=%s", report.ok, len(report.errors))
    return report


def run_doctor_text(project_id: Optional[int] = None) -> str:
    return run_doctor(project_id).as_text()


def generate_system_report(project_id=None) -> str:
    """Backward-compatible alias used by MainWindow."""
    return run_doctor_text(project_id)
