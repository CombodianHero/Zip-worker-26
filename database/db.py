"""Simple database for tracking."""
import sqlite3
from pathlib import Path
from datetime import datetime

class Database:
    def __init__(self):
        self.db_path = Path("database/courses.db")
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT,
                subject TEXT,
                chapter TEXT,
                resource_type TEXT,
                title TEXT,
                url TEXT,
                status TEXT DEFAULT 'pending',
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_item(self, data: dict):
        self.conn.execute(
            "INSERT INTO items (course, subject, chapter, resource_type, title, url, status, file_size) VALUES (?,?,?,?,?,?,?,?)",
            (data.get('course'), data.get('subject'), data.get('chapter'),
             data.get('resource_type'), data.get('title'), data.get('url'),
             data.get('status', 'pending'), data.get('file_size'))
        )
        self.conn.commit()
    
    def get_stats(self):
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
            FROM items
        """)
        row = cursor.fetchone()
        return {'total': row[0] or 0, 'completed': row[1] or 0, 
                'failed': row[2] or 0, 'pending': row[3] or 0}
    
    def get_daily_stats(self):
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM items WHERE date(created_at) = ? AND status = 'completed'",
            (today,)
        )
        downloaded = cursor.fetchone()[0] or 0
        
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM items WHERE date(created_at) = ? AND status = 'failed'",
            (today,)
        )
        failed = cursor.fetchone()[0] or 0
        
        return {'downloaded': downloaded, 'failed': failed}
    
    def close(self):
        self.conn.close()
