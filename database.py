import sqlite3
import os

def sqlite_to_postgres_query(query: str) -> str:
    result = []
    in_single_quote = False
    in_double_quote = False
    escape = False
    for char in query:
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
    return "".join(result)

class CursorWrapper:
    def __init__(self, cursor, is_pg):
        self.cursor = cursor
        self.is_pg = is_pg

    @property
    def description(self):
        return self.cursor.description

    def execute(self, query, params=()):
        if self.is_pg:
            query = sqlite_to_postgres_query(query)
            import re
            query = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', query, flags=re.IGNORECASE)
            query = re.sub(r'\bAUTOINCREMENT\b', '', query, flags=re.IGNORECASE)
            if "INSERT OR IGNORE" in query:
                query = query.replace("INSERT OR IGNORE INTO", "INSERT INTO")
                if "on conflict" not in query.lower():
                    query += " ON CONFLICT DO NOTHING"
        self.cursor.execute(query, params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if not row:
            return None
        if self.is_pg:
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
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql"):
        import psycopg2
        conn = psycopg2.connect(db_url)
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
        reporter_email TEXT DEFAULT 'anonymous@civicfix.org',
        reporter_name TEXT DEFAULT 'Anonymous',
        description TEXT
    )
    """)
    
    # Safely migrate reports table by adding missing columns
    if conn.is_pg:
        # PostgreSQL syntax support
        for col_name, col_type, default_val in [
            ("reporter_email", "TEXT", "'anonymous@civicfix.org'"),
            ("reporter_name", "TEXT", "'Anonymous'"),
            ("description", "TEXT", "NULL")
        ]:
            try:
                cursor.cursor.execute(f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default_val}")
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
    else:
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
    
    if conn.is_pg:
        try:
            cursor.cursor.execute("ALTER TABLE qr_sessions ADD COLUMN IF NOT EXISTS draft_data TEXT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    else:
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
    
    # Safely migrate reports table by adding is_coordinated column
    if conn.is_pg:
        try:
            cursor.cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS is_coordinated INTEGER DEFAULT 0")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    else:
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN is_coordinated INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
    # Create report_approvals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_approvals (
        report_id TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT NOT NULL,
        officer_email TEXT,
        approved_at TEXT,
        PRIMARY KEY (report_id, department)
    )
    """)
    
    # Create reviewers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviewers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        is_available INTEGER DEFAULT 1
    )
    """)
    
    # Create reviewer_assignments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviewer_assignments (
        report_id TEXT NOT NULL,
        reviewer_id TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT NOT NULL,
        resources_logged TEXT,
        completed_at TEXT,
        end_latitude REAL,
        end_longitude REAL,
        analysis_image TEXT,
        PRIMARY KEY (report_id, reviewer_id)
    )
    """)

    # Migrate reviewer_assignments table by adding analysis_image column
    if conn.is_pg:
        try:
            cursor.cursor.execute("ALTER TABLE reviewer_assignments ADD COLUMN IF NOT EXISTS analysis_image TEXT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    else:
        try:
            cursor.execute("ALTER TABLE reviewer_assignments ADD COLUMN analysis_image TEXT")
        except sqlite3.OperationalError:
            pass
    
    # Create fixers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fixers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        is_available INTEGER DEFAULT 1
    )
    """)
    
    # Create fixer_assignments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fixer_assignments (
        report_id TEXT NOT NULL,
        fixer_id TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT NOT NULL,
        completed_at TEXT,
        PRIMARY KEY (report_id, fixer_id)
    )
    """)
    
    # Create coordination_messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coordination_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
