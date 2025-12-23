import sqlite3
from app import app

def migrate():
    print("Migrating database to add 'outcome' column to 'match' table...")
    try:
        conn = sqlite3.connect('instance/v0_backend.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(match)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'outcome' not in columns:
            print("Adding 'outcome' column...")
            cursor.execute("ALTER TABLE match ADD COLUMN outcome VARCHAR(20) DEFAULT 'normal'")
            conn.commit()
            print("Column added successfully.")
        else:
            print("'outcome' column already exists.")
            
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
