import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

AUDIT_DIR = Path(__file__).resolve().parent / "audits"
AUDIT_DIR.mkdir(exist_ok=True)

def _safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"

def write_audit(payload: Dict[str, Any]) -> str:
    """
    Writes an audit JSON file and returns the filesystem path.
    Filename format:
      audit_<applicantname>_<id>_<YYYYMMDD_HHMMSS>.json
    """
    customer = payload.get("customer", {}) or {}
    name_slug = _safe_slug(customer.get("name"))
    cid = customer.get("id", "unknown")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"audit_{name_slug}_{cid}_{ts}.json"
    path = AUDIT_DIR / filename

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
