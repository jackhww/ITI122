import os
import streamlit as st
from pathlib import Path
import subprocess
import sys


from data_connectors import get_credit_record, get_account_record, get_pr_status
from manual_review_writer import write_manual_review_case
from policy_rag import retrieve, build_or_load_index
from decision_engine import call_gemini
from audit_logger import write_audit
from applicant_letter_generator import build_applicant_letter
from decision_note import build_decision_note
from pdf_utils import letter_text_to_pdf_bytes


st.set_page_config(page_title="Loan Risk Assessment (GenAI)", layout="wide")

st.title("Loan Risk Assessment")

st.markdown("""
<style>
/* Metric label */
div[data-testid="stMetricLabel"] {
    font-size: 1.1rem;
}

/* Metric value */
div[data-testid="stMetricValue"] {
    font-size: 2.2rem;
    font-weight: 700;
}

/* Metric delta (if used) */
div[data-testid="stMetricDelta"] {
    font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

def risk_badge(risk: str):
    colors = {
        "low": "🟢 Low",
        "medium": "🟠 Medium",
        "high": "🔴 High",
        "unknown": "⚪ Unknown",
    }
    return colors.get(risk.lower(), risk)

def recommendation_badge(rec: str):
    mapping = {
        "approve": "✅ Approve",
        "do_not_recommend": "⛔ Do Not Recommend",
        "needs_manual_review": "🧐 Needs Manual Review",
    }
    return mapping.get(rec, rec)

with st.sidebar:
    st.header("Setup")
    st.write("1) Ensure DB exists: `python bootstrap_db.py`")
    st.write("2) Set env var: `GEMINI_API_KEY`")
    st.write("3) Put policy PDFs or TXT in `./policies/`")
    if st.button("Rebuild / Load Policy Index"):
        try:
            from policy_rag import rebuild_index
            rebuild_index()
            st.success("Policy index rebuilt")
        except Exception as e:
            st.error(str(e))
    MANUAL_DIR = Path(__file__).resolve().parent / "manual_review_cases"

    if st.sidebar.button("Open manual review folder (path)"):
        st.sidebar.write(str(MANUAL_DIR))


BASE_DIR = Path(__file__).resolve().parent
db_file = BASE_DIR / "bank_systems.db"
if not db_file.exists():
    # Auto-bootstrap DB if missing
    subprocess.check_call([sys.executable, str(BASE_DIR / "bootstrap_db.py")])

customer_id = st.number_input("Customer ID", min_value=1, step=1, value=1111)

if st.button("Assess Risk & Rate"):
    credit = get_credit_record(int(customer_id))
    acct = get_account_record(int(customer_id))

    if not credit or not acct:
        st.error("Customer not found in simulated systems DB.")
        st.stop()

    customer = {
        "id": credit["id"],
        "name": credit["name"],
        "email": credit["email"],
        "credit_score": credit["credit_score"],
        "nationality": acct["nationality"],
        "account_status": acct["account_status"],
    }

    # Conditional PR check
    pr = None
    if customer["nationality"].lower() != "singaporean":
        pr = get_pr_status(int(customer_id))
        customer["pr_status"] = pr

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Retrieved Customer Data (Simulated Systems)")

        # Top summary row
        a, b = st.columns([2, 1])
        with a:
            st.markdown(f"{customer['name']}")
            st.caption(f"Customer ID: {customer['id']} • Email: {customer['email']}")
        with b:
            st.markdown("**Status**")
            st.write(f"**{customer['account_status']}**")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("**Credit Score**", customer["credit_score"])
            st.write(f"**Nationality:** {customer['nationality']}")
        with c2:
            st.write("**Account Status**")
            st.write(customer["account_status"])
            if customer.get("pr_status") is not None:
                st.write("**PR Status**")
                st.write("True" if customer["pr_status"] else "False")
            else:
                st.write("**PR Status**")
                st.write("— (Not required)")
    
    with st.expander("🧾 Data retrieval trace (systems queried)"):
        st.write("Credit Score System → fetched credit_score")
        st.write("Account Status System → fetched account_status & nationality")
        if customer["nationality"].lower() != "singaporean":
            st.write("Government PR Status System → fetched pr_status")
        else:
            st.write(" PR Status check skipped (Singaporean)")


    # RAG query (based on the relevant fields)
    rag_query = f"""
    Determine overall risk and interest rate for:
    credit_score={customer['credit_score']},
    account_status={customer['account_status']},
    nationality={customer['nationality']},
    pr_status={customer.get('pr_status')}
    """

    evidence = retrieve(rag_query, k=5)

    ## Gemini reasoning
    result = call_gemini(customer, evidence)
    # If human review is needed, write a separate case file
    manual_case_path = None
    if result.get("recommendation") == "needs_manual_review":
        manual_case_path = write_manual_review_case(customer, result, evidence, rag_query)

    st.markdown("### Policy Evidence Used")
    for ev in result.get("evidence_used", []):
        with st.expander(f"{ev['chunk_id']}"):
            st.write(ev["why_used"])
    
    with st.expander("View Retrieved Policy Snippets (RAG)"):
        for e in evidence:
            st.markdown(f"**{e['chunk_id']}** (score={e['score']:.3f})")
            st.write(e["text"])
            st.markdown("---")

    st.subheader("Loan Risk Assessment Result")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Overall Risk", risk_badge(result["overall_risk"]))

    with c2:
        st.metric("Interest Rate", result["interest_rate"])

    with c3:
        st.metric("Recommendation", recommendation_badge(result["recommendation"]))

    st.markdown("### Decision Rationale")
    st.write(
        f"""
    **Customer:** {customer['name']} (ID {customer['id']})  
    **Credit Score:** {customer['credit_score']}  
    **Account Status:** {customer['account_status']}  
    **Nationality:** {customer['nationality']}
    """
    )

    if customer.get("pr_status") is not None:
        st.write(f"**PR Status:** {customer['pr_status']}")

    st.info(result["rationale"])


    audit_path = write_audit({
        "customer": customer,
        "rag_query": rag_query,
        "evidence": evidence,
        "result": result,
    })
    st.success(f"Audit saved: {audit_path}")
    if manual_case_path:
        st.warning(f"Sent to manual review queue: {manual_case_path}")

    with st.expander("Audit & Raw Model Output"):
        st.json(result) 
    with st.expander("Internal Audit Note:"):
        decision_note = build_decision_note(customer, result, evidence)
        st.text_area(
            "Decision note:",
            decision_note,
            height=320
        )

        st.download_button(
            label="Download decision note (.txt)",
            data=decision_note.encode("utf-8"),
            file_name=f"decision_note_{customer['id']}.txt",
            mime="text/plain"
        )
    st.markdown("### Applicant-Facing Letter (Formal Communication)")

    applicant_letter = build_applicant_letter(customer, result)

    st.text_area(
        "Applicant letter (formal bank communication):",
        applicant_letter,
        height=320
    )

    colA, colB = st.columns(2)

    with colA:
        st.download_button(
            label="Download applicant letter (.txt)",
            data=applicant_letter.encode("utf-8"),
            file_name=f"applicant_letter_{customer['id']}.txt",
            mime="text/plain"
        )

    with colB:
        pdf_bytes = letter_text_to_pdf_bytes(
            applicant_letter,
            title="Applicant Letter — Loan Application Outcome"
        )
        st.download_button(
            label="Download applicant letter (PDF)",
            data=pdf_bytes,
            file_name=f"applicant_letter_{customer['id']}.pdf",
            mime="application/pdf"
        )


