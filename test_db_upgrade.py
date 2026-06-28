# Projects/civicfix/test_db_upgrade.py
import sys
import os

# Ensure the database module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import database

def test_new_tables_exist():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Check report_approvals
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='report_approvals'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='report_approvals'")
    assert cursor.fetchone() is not None
    
    # Check reviewers
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='reviewers'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviewers'")
    assert cursor.fetchone() is not None
    
    # Check reviewer_assignments
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='reviewer_assignments'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviewer_assignments'")
    assert cursor.fetchone() is not None
    
    # Check fixers
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='fixers'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fixers'")
    assert cursor.fetchone() is not None
    
    # Check fixer_assignments
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='fixer_assignments'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fixer_assignments'")
    assert cursor.fetchone() is not None
    
    # Check coordination_messages
    if conn.is_pg:
        cursor.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='coordination_messages'")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coordination_messages'")
    assert cursor.fetchone() is not None
    
    conn.close()
    print("Database upgrade tables verified successfully!")

if __name__ == "__main__":
    test_new_tables_exist()
