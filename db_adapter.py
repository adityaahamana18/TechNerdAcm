import os, sqlite3
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

# Checks if DATABASE_URL or SUPABASE_DB_URL is present in environment
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
SQLITE_DB = os.path.join(os.path.dirname(__file__), "technerd.db")

class DBConnectionWrapper:
    """Wrapper that normalizes SQLite and PostgreSQL (Supabase) access"""
    def __init__(self, conn, is_pg=False):
        self.conn = conn
        self.is_pg = is_pg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

    def execute(self, sql, params=()):
        if self.is_pg:
            # Convert SQLite '?' parameter placeholders to PostgreSQL '%s'
            pg_sql = sql.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(pg_sql, params)
            return cur
        else:
            return self.conn.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        if self.is_pg:
            pg_sql = sql.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.executemany(pg_sql, seq_of_params)
            return cur
        else:
            return self.conn.executemany(sql, seq_of_params)

def get_db():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if db_url and psycopg2:
        try:
            # Handle render/supabase 'postgres://' vs 'postgresql://' prefix
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            conn = psycopg2.connect(db_url, sslmode="require")
            return DBConnectionWrapper(conn, is_pg=True)
        except Exception as e:
            print(">>> Could not connect to Supabase PostgreSQL, using local SQLite fallback:", e)

    conn = sqlite3.connect(SQLITE_DB, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return DBConnectionWrapper(conn, is_pg=False)

def is_postgres():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    return bool(db_url and psycopg2)

