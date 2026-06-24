import database
import os

def test_initialization():
    # Force fresh init
    if os.path.exists("/tmp/civicfix.db"):
        os.remove("/tmp/civicfix.db")
    database.init_db()
    
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "reports" in tables
    assert "qr_sessions" in tables
    assert "leaderboard" in tables
    
    # Check reports columns
    cursor.execute("PRAGMA table_info(reports)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "reporter_email" in columns
    assert "reporter_name" in columns
    
    # Check leaderboard columns
    cursor.execute("PRAGMA table_info(leaderboard)")
    lead_cols = [row[1] for row in cursor.fetchall()]
    assert "email" in lead_cols
    assert "avatar_url" in lead_cols
    print("Test passed: Database initialized correctly and columns verified.")

if __name__ == "__main__":
    test_initialization()
