# scripts/inspect_checkpoints.py
"""Inspect the LangGraph checkpoint database."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "data" / "checkpoints.db"
conn = sqlite3.connect(str(db_path))

print("=== Tables ===")
for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(f"  {name}")

print("\n=== Row counts ===")
for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    (count,) = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
    print(f"  {name}: {count} rows")

print("\n=== Threads and their checkpoint counts ===")
for row in conn.execute("SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id"):
    print(f"  {row[0]}: {row[1]} checkpoints")

conn.close()