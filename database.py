import sqlite3
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

class CursorWrapper:
    def __init__(self, cursor, is_pg):
        self.cursor = cursor
        self.is_pg = is_pg

    def execute(self, query, params=()):
        if self.is_pg:
            # Convert SQLite placeholder ? to PostgreSQL placeholder %s
            query = query.replace("?", "%s")
            # Convert SQLite specific INSERT OR IGNORE to PostgreSQL ON CONFLICT DO NOTHING
            if "INSERT OR IGNORE" in query:
                query = query.replace("INSERT OR IGNORE INTO leaderboard", "INSERT INTO leaderboard")
                query += " ON CONFLICT (username) DO NOTHING"
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
        db_path = os.environ.get("DB_PATH", "/tmp/civicfix.db")
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
        updated_at TEXT NOT NULL
    )
    """)
    
    # Create qr_sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qr_sessions (
        token TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        associated_report_id TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Create leaderboard table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leaderboard (
        username TEXT PRIMARY KEY,
        civic_points INTEGER DEFAULT 0,
        reports_submitted INTEGER DEFAULT 0
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
