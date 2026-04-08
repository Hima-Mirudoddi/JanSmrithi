import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST')
user = os.getenv('DB_USER', 'avnadmin')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'defaultdb')
port = int(os.getenv('DB_PORT', 3306)) # Or 25060 depending on your Aiven setup

print(f"Connecting to Aiven MySQL database at {host}...")

try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        with open('schema_mysql.sql', 'r') as f:
            sql_statements = f.read().split(';')
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
    print("\nSUCCESS: All tables created perfectly in your Aiven Database!")
except Exception as e:
    print(f"Error: {e}")
    print("\nPlease verify your .env file credentials and try again.")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
