import sqlite3
import os

def get_db():
    db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "civicfix.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        image_path TEXT NOT NULL,
        resolved_image_path TEXT,
        tags TEXT NOT NULL,
        department TEXT NOT NULL,
        priority INTEGER NOT NULL,
        votes INTEGER DEFAULT 1,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        reporter_email TEXT DEFAULT 'anonymous@civicfix.org',
        reporter_name TEXT DEFAULT 'Anonymous',
        description TEXT
    )
    """)
    
    # Safely migrate reports table by adding missing columns
    for col_def in [
        "ALTER TABLE reports ADD COLUMN reporter_email TEXT DEFAULT 'anonymous@civicfix.org'",
        "ALTER TABLE reports ADD COLUMN reporter_name TEXT DEFAULT 'Anonymous'",
        "ALTER TABLE reports ADD COLUMN description TEXT"
    ]:
        try:
            cursor.execute(col_def)
        except sqlite3.OperationalError:
            pass  # Column already exists
            
    # Create qr_sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qr_sessions (
        token TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        associated_report_id TEXT,
        created_at TEXT NOT NULL,
        draft_data TEXT
    )
    """)
    
    try:
        cursor.execute("ALTER TABLE qr_sessions ADD COLUMN draft_data TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Recreate leaderboard table with email primary key
    cursor.execute("DROP TABLE IF EXISTS leaderboard")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leaderboard (
        email TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        avatar_url TEXT NOT NULL,
        civic_points INTEGER DEFAULT 0,
        reports_submitted INTEGER DEFAULT 0
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
