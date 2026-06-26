import sqlite3
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def sqlite_to_postgres_query(query: str) -> str:
    result = []
    in_single_quote = False
    in_double_quote = False
    escape = False
    i = 0
    while i < len(query):
        char = query[i]
        if escape:
            result.append(char)
            escape = False
        elif char == '\\':
            result.append(char)
            escape = True
        elif char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append(char)
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(char)
        elif char == '?' and not in_single_quote and not in_double_quote:
            result.append('%s')
        else:
            result.append(char)
        i += 1
    return "".join(result)

class CursorWrapper:
    def __init__(self, cursor, is_pg):
        self.cursor = cursor
        self.is_pg = is_pg

    def execute(self, query, params=()):
        if self.is_pg:
            query = sqlite_to_postgres_query(query)
            if "INSERT OR IGNORE" in query:
                query = query.replace("INSERT OR IGNORE INTO leaderboard", "INSERT INTO leaderboard")
                query += " ON CONFLICT (email) DO NOTHING"
        self.cursor.execute(query, params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if not row:
            return None
        if self.is_pg:
            # Map column names to values to replicate dict-like interface of sqlite3.Row
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.is_pg:
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return rows

    def close(self):
        self.cursor.close()

class ConnectionWrapper:
    def __init__(self, conn, is_pg):
        self.conn = conn
        self.is_pg = is_pg

    def cursor(self):
        return CursorWrapper(self.conn.cursor(), self.is_pg)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return ConnectionWrapper(conn, is_pg=True)
    else:
        db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "civicfix.db"))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return ConnectionWrapper(conn, is_pg=False)

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
        description TEXT
    )
    """)
    
    # Safely migrate reports table by adding missing columns
    if conn.is_pg:
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_email TEXT")
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_name TEXT")
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS description TEXT")
    else:
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN reporter_email TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN reporter_name TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN description TEXT")
        except Exception:
            pass

    # Create qr_sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qr_sessions (
        token TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        associated_report_id TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Safely migrate qr_sessions by adding draft_data column
    if conn.is_pg:
        cursor.execute("ALTER TABLE qr_sessions ADD COLUMN IF NOT EXISTS draft_data TEXT")
    else:
        try:
            cursor.execute("ALTER TABLE qr_sessions ADD COLUMN draft_data TEXT")
        except Exception:
            pass
    
    # We drop the old leaderboard table if it doesn't have the new layout
    try:
        # Check if new columns exist
        cursor.execute("SELECT email FROM leaderboard LIMIT 1")
    except Exception:
        # Table doesn't exist or is old format, recreate it
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
