import os
print(f'Current dir: {os.getcwd()}')
print(f'Data dir exists: {os.path.exists("data")}')
print(f'Database URL: {os.environ.get("DATABASE_URL", "Not set")}')

# Test SQLite
import sqlite3
try:
    conn = sqlite3.connect('data/mermaid_converter.db')
    print('✅ SQLite works!')
    conn.close()
except Exception as e:
    print(f'❌ SQLite error: {e}')
