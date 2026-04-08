import sqlite3
import os

print("Connecting to local SQLite database jansmrithi.db...", flush=True)

# Read the schema.sql file
with open('schema.sql', 'r') as file:
    sql_script = file.read()

try:
    connection = sqlite3.connect('jansmrithi.db')
    cursor = connection.cursor()
    cursor.executescript(sql_script)
    connection.commit()
    print("\nSUCCESS: All tables created perfectly! You are ready to deploy manually.")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'connection' in locals() and connection:
        connection.close()
