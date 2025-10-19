#!/usr/bin/env python3
"""Migration script to remove uipath_folder_path column from users table.

This script:
1. Creates a backup of the users table
2. Creates a new users table without uipath_folder_path
3. Copies data from old table to new table
4. Drops old table and renames new table
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str):
    """Remove uipath_folder_path column from users table.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Starting migration for: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'uipath_folder_path' not in columns:
            print("✅ Column 'uipath_folder_path' does not exist. No migration needed.")
            return
        
        print("📋 Column 'uipath_folder_path' found. Starting migration...")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Create new users table without uipath_folder_path
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                uipath_url TEXT,
                uipath_access_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
            INSERT INTO users_new (
                id, username, email, hashed_password, role, is_active,
                uipath_url, uipath_access_token, created_at, updated_at
            )
            SELECT 
                id, username, email, hashed_password, role, is_active,
                uipath_url, uipath_access_token, created_at, updated_at
            FROM users
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE users")
        
        # Rename new table
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # Recreate index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username 
            ON users(username)
        """)
        
        # Commit transaction
        conn.commit()
        
        print("✅ Migration completed successfully!")
        print("   - Removed 'uipath_folder_path' column from users table")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    # Default database path
    db_path = "database/mcp_servers.db"
    
    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    migrate_database(db_path)
