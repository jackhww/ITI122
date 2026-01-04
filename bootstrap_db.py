import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bank_systems.db"

CREDIT_ROWS = [
    (1111, "Loren", "loren@gmail.com", 455),
    (2222, "Matt", "matt@yahoo.com", 685),
    (3333, "Hilda", "halida@gmail.com", 825),
    (4444, "Andy", "andy@gmail.com", 840),
    (5555, "Kit", "kit@yahho.com", 350),
]

ACCOUNT_ROWS = [
    (1111, "Loren", "Singaporean", "loren@gmail.com", "good-standing"),
    (2222, "Matt", "Non-Singaporean", "matt@yahoo.com", "closed"),
    (3333, "Hilda", "Singaporean", "halida@gmail.com", "delinquent"),
    (4444, "Andy", "Non-Singaporean", "andy@gmail.com", "good-standing"),
    (5555, "Kit", "Singaporean", "kit@yahho.com", "delinquent"),
]

PR_ROWS = [
    (2222, "Matt", "matt@yahoo.com", 1),
    (4444, "Andy", "andy@gmail.com", 0),
]

def main():
    print("Writing DB to:", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit_scores (
      id INTEGER PRIMARY KEY,
      name TEXT,
      email TEXT,
      credit_score INTEGER
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS account_status (
      id INTEGER PRIMARY KEY,
      name TEXT,
      nationality TEXT,
      email TEXT,
      account_status TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pr_status (
      id INTEGER PRIMARY KEY,
      name TEXT,
      email TEXT,
      pr_status INTEGER
    )""")

    # Reset + insert
    cur.execute("DELETE FROM credit_scores")
    cur.execute("DELETE FROM account_status")
    cur.execute("DELETE FROM pr_status")

    cur.executemany("INSERT INTO credit_scores VALUES (?,?,?,?)", CREDIT_ROWS)
    cur.executemany("INSERT INTO account_status VALUES (?,?,?,?,?)", ACCOUNT_ROWS)
    cur.executemany("INSERT INTO pr_status VALUES (?,?,?,?)", PR_ROWS)

    conn.commit()

    # Verify counts
    for t in ["credit_scores", "account_status", "pr_status"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n} rows")

    conn.close()
    print("✅ Bootstrap complete")

if __name__ == "__main__":
    main()
