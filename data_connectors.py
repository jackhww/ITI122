import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bank_systems.db"



def _fetchone(query: str, params: tuple) -> Optional[tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row

def get_credit_record(customer_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        "SELECT id, name, email, credit_score FROM credit_scores WHERE id=?",
        (customer_id,),
    )
    if not row:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "credit_score": row[3]}

def get_account_record(customer_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        "SELECT id, name, nationality, email, account_status FROM account_status WHERE id=?",
        (customer_id,),
    )
    if not row:
        return None
    return {"id": row[0], "name": row[1], "nationality": row[2], "email": row[3], "account_status": row[4]}

def get_pr_status(customer_id: int) -> Optional[bool]:
    row = _fetchone(
        "SELECT pr_status FROM pr_status WHERE id=?",
        (customer_id,),
    )
    if not row:
        return None
    return bool(row[0])
