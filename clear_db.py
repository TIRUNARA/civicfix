import database

def clear():
    conn = database.get_db()
    cursor = conn.cursor()
    tables = [
        "reports", 
        "qr_sessions", 
        "leaderboard", 
        "report_approvals", 
        "reviewer_assignments", 
        "fixer_assignments", 
        "coordination_messages", 
        "reviewers", 
        "fixers"
    ]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared {table}")
        except Exception as e:
            print(f"Error clearing {table}: {e}")
            if conn.is_pg:
                try:
                    conn.rollback()
                except Exception:
                    pass
    conn.commit()
    conn.close()

    # Re-run init_db to seed reviewers and fixers
    database.init_db()
    print("Database re-initialized and seeded.")

if __name__ == "__main__":
    clear()
