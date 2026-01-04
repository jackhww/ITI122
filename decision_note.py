from typing import Dict, Any, List

def build_decision_note(
    customer: Dict[str, Any],
    result: Dict[str, Any],
    evidence: List[Dict[str, Any]],
) -> str:
    # Keep citations short and traceable
    evidence_refs = []
    for ev in (result.get("evidence_used") or []):
        evidence_refs.append(f"- {ev.get('chunk_id')}: {ev.get('why_used')}")

    pr_line = ""
    if customer.get("pr_status") is not None:
        pr_line = f"PR Status: {'True' if customer.get('pr_status') else 'False'}\n"

    note = f"""\
INTERNAL DECISION NOTE — LOAN RISK ASSESSMENT

Customer Details
- Name: {customer.get('name')}
- Customer ID: {customer.get('id')}
- Email: {customer.get('email')}
- Nationality: {customer.get('nationality')}
{('- ' + pr_line) if pr_line else ""}- Credit Score: {customer.get('credit_score')}
- Account Status: {customer.get('account_status')}

Assessment Outcome
- Overall Risk Level: {result.get('overall_risk')}
- Applicable Interest Rate: {result.get('interest_rate')}
- Recommendation: {result.get('recommendation')}

Rationale
{result.get('rationale')}

Policy Evidence Referenced
{chr(10).join(evidence_refs) if evidence_refs else "- (No structured evidence references returned)"}

Assumptions / Gaps
{chr(10).join(['- ' + g for g in (result.get('assumptions_or_gaps') or [])]) if (result.get('assumptions_or_gaps') or []) else "- None"}

Prepared by: GenAI Risk Assistant (Prototype (Self-host + Gemini))
"""
    return "\n".join([line.rstrip() for line in note.splitlines()])
