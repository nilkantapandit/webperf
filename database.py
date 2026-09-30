import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent

_raw_db_path = __import__('os').getenv('DATABASE_PATH', '').strip()
DB_PATH = Path(_raw_db_path) if _raw_db_path else (BASE_DIR / 'webperf.db')
if not DB_PATH.is_absolute():
    DB_PATH = (BASE_DIR / DB_PATH).resolve()


def database_path():
    return str(DB_PATH)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            premium_unlocked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL DEFAULT 'razorpay',
            order_id TEXT UNIQUE,
            payment_id TEXT,
            amount_minor INTEGER NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status);

        CREATE TABLE IF NOT EXISTS competitor_cache (
            cache_key TEXT PRIMARY KEY,
            region TEXT NOT NULL,
            industry TEXT NOT NULL,
            results_json TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_cache (
            cache_key TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website_host TEXT NOT NULL,
            checked_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_events_checked_at ON analysis_events(checked_at);
        ''')


def get_user_by_id(user_id):
    with connect() as conn:
        return conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()


def get_user_by_email(email):
    with connect() as conn:
        return conn.execute('SELECT * FROM users WHERE lower(email) = lower(?)', (email,)).fetchone()


def create_user(email, password_hash):
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            'INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)',
            (email.lower().strip(), password_hash, now),
        )
        return cur.lastrowid


def set_premium(user_id, unlocked=True):
    with connect() as conn:
        conn.execute('UPDATE users SET premium_unlocked = ? WHERE id = ?', (1 if unlocked else 0, user_id))


def create_purchase(user_id, order_id, amount_minor, currency, status='created'):
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            '''INSERT INTO purchases
               (user_id, order_id, amount_minor, currency, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, order_id, amount_minor, currency, status, now, now),
        )
        return cur.lastrowid


def get_purchase_by_order(order_id):
    with connect() as conn:
        return conn.execute('SELECT * FROM purchases WHERE order_id = ?', (order_id,)).fetchone()


def mark_purchase_paid(order_id, payment_id):
    now = utc_now()
    with connect() as conn:
        row = conn.execute('SELECT user_id FROM purchases WHERE order_id = ?', (order_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            'UPDATE purchases SET payment_id = ?, status = ?, updated_at = ? WHERE order_id = ?',
            (payment_id, 'captured', now, order_id),
        )
        conn.execute('UPDATE users SET premium_unlocked = 1 WHERE id = ?', (row['user_id'],))
        return row['user_id']


def list_users(limit=100):
    with connect() as conn:
        return conn.execute(
            '''SELECT u.id, u.email, u.premium_unlocked, u.created_at,
                      COUNT(p.id) AS purchase_count,
                      MAX(CASE WHEN p.status = 'captured' THEN p.created_at END) AS last_purchase
               FROM users u
               LEFT JOIN purchases p ON p.user_id = u.id
               GROUP BY u.id
               ORDER BY u.created_at DESC
               LIMIT ?''',
            (limit,),
        ).fetchall()


def list_purchases(limit=100):
    with connect() as conn:
        return conn.execute(
            '''SELECT p.*, u.email
               FROM purchases p
               JOIN users u ON u.id = p.user_id
               ORDER BY p.created_at DESC
               LIMIT ?''',
            (limit,),
        ).fetchall()


def stats():
    with connect() as conn:
        users = conn.execute('SELECT COUNT(*) AS n FROM users').fetchone()['n']
        premium = conn.execute('SELECT COUNT(*) AS n FROM users WHERE premium_unlocked = 1').fetchone()['n']
        captured = conn.execute("SELECT COUNT(*) AS n FROM purchases WHERE status = 'captured'").fetchone()['n']
        return {'users': users, 'premium_users': premium, 'captured_purchases': captured}


def record_analysis_event(website_host):
    now = datetime.now(timezone.utc)
    cutoff = datetime.fromtimestamp(now.timestamp() - 172800, timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            'INSERT INTO analysis_events (website_host, checked_at) VALUES (?, ?)',
            (str(website_host or '').strip().lower(), now.isoformat()),
        )
        conn.execute('DELETE FROM analysis_events WHERE checked_at < ?', (cutoff,))


def checks_last_hour():
    cutoff = datetime.now(timezone.utc).timestamp() - 3600
    cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()
    with connect() as conn:
        row = conn.execute(
            'SELECT COUNT(*) AS n FROM analysis_events WHERE checked_at >= ?',
            (cutoff_iso,),
        ).fetchone()
        return int(row['n'] or 0)


def get_cache(cache_key, table='competitor_cache'):
    with connect() as conn:
        row = conn.execute(f'SELECT * FROM {table} WHERE cache_key = ?', (cache_key,)).fetchone()
        if not row:
            return None
        try:
            expires = datetime.fromisoformat(row['expires_at'])
        except ValueError:
            return None
        if expires <= datetime.now(timezone.utc):
            conn.execute(f'DELETE FROM {table} WHERE cache_key = ?', (cache_key,))
            return None
        return row


def set_competitor_cache(cache_key, region, industry, results, expires_at):
    now = utc_now()
    with connect() as conn:
        conn.execute(
            '''INSERT INTO competitor_cache (cache_key, region, industry, results_json, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET
                 results_json=excluded.results_json,
                 expires_at=excluded.expires_at,
                 created_at=excluded.created_at''',
            (cache_key, region, industry, json.dumps(results), expires_at, now),
        )


def set_analysis_cache(cache_key, result, expires_at):
    now = utc_now()
    with connect() as conn:
        conn.execute(
            '''INSERT INTO analysis_cache (cache_key, result_json, expires_at, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET
                 result_json=excluded.result_json,
                 expires_at=excluded.expires_at,
                 created_at=excluded.created_at''',
            (cache_key, json.dumps(result), expires_at, now),
        )
