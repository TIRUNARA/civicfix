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
    print("Test passed: Database initialized correctly.")

if __name__ == "__main__":
    test_initialization()
