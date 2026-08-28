# ui/scrap_events_hook.py
"""Shared emit helper for scrap mutations (imported by scrap_manager if needed)."""

def emit_scrap_changed(project_id=None, reason="scrap"):
    try:
        from utils.events import bus
        bus.emit("scrap.changed", {"project_id": project_id, "reason": reason})
        bus.emit("ui.refresh_request", {"reason": reason, "project_id": project_id})
    except Exception:
        pass
