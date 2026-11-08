import sqlite3

conn = sqlite3.connect(r"D:\matrix_data\matrix.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables in D:\\matrix_data\\matrix.db:", tables)

for t in ["devices", "background_tasks", "sessions", "messages", "security_audit_logs"]:
    if t in tables:
        c.execute(f"PRAGMA table_info({t})")
        cols = [f"{col[1]} ({col[2]})" for col in c.fetchall()]
        print(f"Table '{t}': {', '.join(cols)}")
    else:
        print(f"Table '{t}': NOT FOUND")

conn.close()
