import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

AUDIT_DIR = Path("audits")
AUDIT_DIR.mkdir(exist_ok=True)

def write_audit(payload: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = AUDIT_DIR / f"audit_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
