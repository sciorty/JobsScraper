import sqlite3
import threading
from typing import List, Dict, Any

DB_PATH = 'jobs.db'
_lock = threading.Lock()

def init_db():
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            posted_date TEXT,
            reviewed INTEGER DEFAULT 0,
            interested INTEGER DEFAULT 0,
            comment TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # Add new columns if they don't exist (for existing DBs)
        c.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in c.fetchall()}
        
        if 'reviewed' not in columns:
            c.execute("ALTER TABLE jobs ADD COLUMN reviewed INTEGER DEFAULT 0")
        if 'interested' not in columns:
            c.execute("ALTER TABLE jobs ADD COLUMN interested INTEGER DEFAULT 0")
        
        # Remove old 'flag' column if it exists and migrate data
        if 'flag' in columns and 'interested' in columns:
            try:
                c.execute("UPDATE jobs SET interested = flag WHERE interested = 0 AND flag = 1")
            except:
                pass
        
        # Create app_config table for storing configuration in DB
        c.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

def get_config(key: str, default=None):
    """Get a config value from DB"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT value FROM app_config WHERE key = ?', (key,))
        row = c.fetchone()
        conn.close()
        if row:
            import json
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return default

def set_config(key: str, value):
    """Set a config value in DB (saves with JSON serialization)"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        import json
        json_value = json.dumps(value)
        c.execute('INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)', (key, json_value))
        conn.commit()
        conn.close()

def get_all_config():
    """Get all config from app_config table"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT key, value FROM app_config')
        rows = c.fetchall()
        conn.close()
        result = {}
        import json
        for key, value in rows:
            try:
                result[key] = json.loads(value)
            except:
                result[key] = value
        return result

def upsert_jobs(jobs: List[Dict[str, Any]]):
    """Insert jobs, deduplicating by (title, company, location, posted_date) fingerprint"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get existing job fingerprints to avoid duplicates
        c.execute('''
        SELECT title, company, location, posted_date FROM jobs
        ''')
        existing = set()
        for row in c.fetchall():
            existing.add((row[0], row[1], row[2], row[3]))
        
        inserted = 0
        for job in jobs:
            fingerprint = (job.get('title'), job.get('company'), job.get('location'), job.get('posted_date'))
            
            # Skip if already exists
            if fingerprint in existing:
                continue
                
            try:
                c.execute('''
                INSERT OR IGNORE INTO jobs (title, company, location, url, posted_date, reviewed, interested)
                VALUES (?, ?, ?, ?, ?, 0, 0)
                ''', (job.get('title'), job.get('company'), job.get('location'), job.get('url'), job.get('posted_date')))
                inserted += 1
                existing.add(fingerprint)
            except Exception:
                pass
        
        conn.commit()
        conn.close()
        return inserted

def list_jobs(filter_by: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        query = 'SELECT * FROM jobs ORDER BY created_at DESC'
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def set_flag(job_id: int, flag: int):
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE jobs SET flag = ? WHERE id = ?', (flag, job_id))
        conn.commit()
        conn.close()

def set_reviewed(job_id: int, reviewed: int):
    """Mark job as reviewed"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE jobs SET reviewed = ? WHERE id = ?', (reviewed, job_id))
        conn.commit()
        conn.close()

def set_interested(job_id: int, interested: int):
    """Mark job as interested"""
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE jobs SET interested = ? WHERE id = ?', (interested, job_id))
        conn.commit()
        conn.close()

def set_comment(job_id: int, comment: str):
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE jobs SET comment = ? WHERE id = ?', (comment, job_id))
        conn.commit()
        conn.close()
