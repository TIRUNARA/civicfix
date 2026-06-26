import database
import os

def test_initialization():
    # Force fresh init
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

    # Check qr_sessions columns
    cursor.execute("PRAGMA table_info(qr_sessions)")
    qr_cols = [row[1] for row in cursor.fetchall()]
    assert "draft_data" in qr_cols
    print("Test passed: Database initialized correctly and columns verified.")

def test_sqlite_to_postgres_query():
    # Simple replacement
    q1 = "SELECT * FROM reports WHERE id = ?"
    r1 = database.sqlite_to_postgres_query(q1)
    assert r1 == "SELECT * FROM reports WHERE id = %s"

    # Placeholders inside quotes should NOT be replaced
    q2 = "SELECT * FROM reports WHERE id = ? AND description = 'Is this a pothole?'"
    r2 = database.sqlite_to_postgres_query(q2)
    assert r2 == "SELECT * FROM reports WHERE id = %s AND description = 'Is this a pothole?'"

    # Double quotes inside SQL
    q3 = 'SELECT * FROM reports WHERE id = ? AND tags = "pothole?"'
    r3 = database.sqlite_to_postgres_query(q3)
    assert r3 == 'SELECT * FROM reports WHERE id = %s AND tags = "pothole?"'
    
    print("Test passed: SQLite to Postgres query conversion tokenizer verified.")

if __name__ == "__main__":
    test_initialization()
    test_sqlite_to_postgres_query()
