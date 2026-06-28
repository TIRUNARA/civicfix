import database
import os

def test_initialization():
    db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(database.__file__), "civicfix.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_db()
    
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "reports" in tables
    assert "qr_sessions" in tables
    assert "leaderboard" in tables
    
    cursor.execute("PRAGMA table_info(reports)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "reporter_email" in columns
    assert "reporter_name" in columns
    
    cursor.execute("PRAGMA table_info(leaderboard)")
    lead_cols = [row[1] for row in cursor.fetchall()]
    assert "email" in lead_cols
    assert "avatar_url" in lead_cols
    print("Test passed: Database initialized correctly and columns verified.")

if __name__ == "__main__":
    test_initialization()
