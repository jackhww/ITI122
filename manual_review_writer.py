import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

MANUAL_DIR = Path(__file__).resolve().parent / "manual_review_cases"
MANUAL_DIR.mkdir(exist_ok=True)

def write_manual_review_case(
    customer: Dict[str, Any],
    result: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    rag_query: str,
) -> str:
    """
    Writes a manual review case file for a human reviewer.
    Returns the filepath as a string.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cid = customer.get("id", "unknown")
    path = MANUAL_DIR / f"manual_review_{cid}_{ts}.json"

    payload = {
        "timestamp": ts,
        "customer": customer,
        "rag_query": rag_query,
        "decision": {
            "overall_risk": result.get("overall_risk"),
            "interest_rate": result.get("interest_rate"),
            "recommendation": result.get("recommendation"),
            "rationale": result.get("rationale"),
            "assumptions_or_gaps": result.get("assumptions_or_gaps", []),
        },
        "evidence": [
            {
                "chunk_id": e.get("chunk_id"),
                "source": e.get("source"),
                "score": e.get("score"),
                "text_preview": (e.get("text") or "")[:1200],
            }
            for e in evidence
        ],
        "evidence_used": result.get("evidence_used", []),
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
