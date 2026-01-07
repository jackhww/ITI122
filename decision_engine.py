import json
import os
from typing import Dict, Any, List
import re

import google.generativeai as genai

SYSTEM_INSTRUCTIONS = """You are a bank loan risk assistant.
Rules:
- Use ONLY the provided customer data and policy evidence.
- If policy evidence is insufficient, say what is missing.
- Output must be strict JSON with the required fields.
If the Interest Rate policy includes a “be conservative if between categories” note, follow it.
Recommendation policy:
- If overall_risk is low or medium and account_status is not delinquent -> recommendation MUST be "approve"
- If overall_risk is high OR account_status is delinquent -> "needs_manual_review"
- If nationality is Non-Singaporean and PR status is false -> "do_not_recommend"
Return ONLY JSON.
"""

PREFERRED_ORDER = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
]


def _extract_json(text: str) -> str:
    text = (text or "").strip()

    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if fence:
        return fence.group(1).strip()

    # If no fences, try to find first JSON object
    obj = re.search(r"(\{[\s\S]*\})", text)
    if obj:
        return obj.group(1).strip()

    return text

def deterministic_recommendation(customer: dict, overall_risk: str) -> str:
    nat = (customer.get("nationality") or "").lower()
    acct = (customer.get("account_status") or "").lower()
    pr = customer.get("pr_status", None)

    if "non" in nat and "singapore" in nat and pr is False:
        return "do_not_recommend"

    if overall_risk == "high":
        return "needs_manual_review"

    # If delinquent, force review even if model says otherwise
    if "delinquent" in acct:
        return "needs_manual_review"

    if overall_risk in ("low", "medium"):
        return "approve"

    return "needs_manual_review"


def pick_model_name() -> str:
    available = {m.name: m for m in genai.list_models()}
    for name in PREFERRED_ORDER:
        m = available.get(name)
        if m and "generateContent" in getattr(m, "supported_generation_methods", []):
            return name
    for m in available.values():
        if "generateContent" in getattr(m, "supported_generation_methods", []):
            return m.name
    raise RuntimeError("No available Gemini models support generateContent for this API key.")

def call_gemini(customer: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY env var.")
    genai.configure(api_key=api_key)

    model_name = pick_model_name()

    evidence_block = [{
        "chunk_id": e["chunk_id"],
        "source": e["source"],
        "text": e["text"][:900],
    } for e in evidence]

    prompt = {
        "task": "Assess overall risk level and interest rate, and produce rationale grounded in evidence.",
        "customer": customer,
        "policy_evidence": evidence_block,
        "required_output_json_schema": {
            "customer_id": "int",
            "overall_risk": "low|medium|high|unknown",
            "interest_rate": "string percent or 'unknown'",
            "recommendation": "approve|do_not_recommend|needs_manual_review",
            "rationale": "string",
            "evidence_used": [{"chunk_id": "string", "why_used": "string"}],
            "assumptions_or_gaps": ["string"]
        }
    }

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTIONS
    )

    resp = model.generate_content(json.dumps(prompt))
    raw = (resp.text or "").strip()

    try:
        cleaned = _extract_json(raw)
        result = json.loads(cleaned)

        result["recommendation"] = deterministic_recommendation(
            customer,
            (result.get("overall_risk") or "unknown").lower()
        )
        return result
    except Exception as e:
        return {
            "customer_id": customer.get("id"),
            "overall_risk": "unknown",
            "interest_rate": "unknown",
            "recommendation": "needs_manual_review",
            "rationale": f"Model output was not valid JSON even after cleaning. Used model: {model_name}. Error: {type(e).__name__}",
            "evidence_used": [],
            "assumptions_or_gaps": [raw[:2000]],
        }
