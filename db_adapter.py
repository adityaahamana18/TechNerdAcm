import os, sqlite3

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

def get_database_url():
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

SQLITE_DB = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "technerd.db"))

class CursorWrapper:
    """Wraps cursor fetch calls so dictionary and tuple/Row access work consistently."""
    def __init__(self, cur, is_pg=False):
        self.cur = cur
        self.is_pg = is_pg

    @property
    def lastrowid(self):
        if self.is_pg:
            try:
                row = self.cur.fetchone()
                if row:
                    return row.get("id") if isinstance(row, dict) else row[0]
            except Exception:
                pass
            return None
        return getattr(self.cur, "lastrowid", None)

    def fetchone(self):
        r = self.cur.fetchone()
        if r is None:
            return None
        return r

    def fetchall(self):
        return self.cur.fetchall()

    def __iter__(self):
        return iter(self.cur)

class DBConnectionWrapper:
    """Wrapper that normalizes SQLite and PostgreSQL (Supabase) access seamlessly."""
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
            # If inserting and no returning clause, add RETURNING id for lastrowid
            if pg_sql.strip().upper().startswith("INSERT INTO") and "RETURNING" not in pg_sql.upper():
                pg_sql += " RETURNING id"
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(pg_sql, params)
            return CursorWrapper(cur, is_pg=True)
        else:
            return self.conn.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        if self.is_pg:
            pg_sql = sql.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.executemany(pg_sql, seq_of_params)
            return CursorWrapper(cur, is_pg=True)
        else:
            return self.conn.executemany(sql, seq_of_params)

    def executescript(self, script):
        if self.is_pg:
            cur = self.conn.cursor()
            cur.execute(script)
        else:
            self.conn.executescript(script)

def get_db():
    db_url = get_database_url()
    if db_url and psycopg2:
        try:
            conn = psycopg2.connect(db_url, sslmode="require")
            return DBConnectionWrapper(conn, is_pg=True)
        except Exception as e:
            print(">>> [DB_ADAPTER] Supabase connection error, falling back to SQLite:", e)

    conn = sqlite3.connect(SQLITE_DB, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return DBConnectionWrapper(conn, is_pg=False)

def is_postgres():
    return bool(get_database_url() and psycopg2)

