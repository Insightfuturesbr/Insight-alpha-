# scripts/migrate_001_add_owner_created_at.py
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset", "strategies.db")
DB_PATH = os.path.abspath(DB_PATH)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

def col_exists(table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

# Adiciona strategies.owner (NOT NULL com default)
if not col_exists("strategies", "owner"):
    cur.execute("ALTER TABLE strategies ADD COLUMN owner TEXT NOT NULL DEFAULT 'anonimo'")

# Adiciona strategies.created_at se ainda não existir
if not col_exists("strategies", "created_at"):
    cur.execute("ALTER TABLE strategies ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

con.commit()
con.close()
print("Migração aplicada com sucesso.")
