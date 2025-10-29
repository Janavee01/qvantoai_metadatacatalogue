import sqlite3

# Connect to database
conn = sqlite3.connect("metadata.db")
cursor = conn.cursor()

# Create assets table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,
    tags TEXT,
    description TEXT
)
""")

conn.commit()
conn.close()
print("Table 'assets' created successfully")
