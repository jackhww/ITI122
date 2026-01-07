import re
from pathlib import Path
import json
from datetime import datetime

def _safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"

def write_manual_review_case(customer, result, evidence, rag_query):
    out_dir = Path(__file__).resolve().parent / "manual_review_cases"
    out_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_slug = _safe_slug(customer.get("name"))
    cid = customer.get("id", "unknown")

    # filename format:
    # manual_review_name_id_ts.json
    filename = f"manual_review_{name_slug}_{cid}_{ts}.json"
    path = out_dir / filename

    payload = {
        "timestamp": ts,
        "customer": customer,
        "rag_query": rag_query,
        "decision": result,
        "evidence": [
            {
                "chunk_id": e.get("chunk_id"),
                "source": e.get("source"),
                "score": e.get("score"),
                "text_preview": (e.get("text") or "")[:1200],
            } for e in evidence
        ],
        "evidence_used": result.get("evidence_used", []),
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
