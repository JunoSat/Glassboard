import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from app.config import Config

_pool = None # This variable will store the connection pool decrlaring before to later check status


'''
Because init_pool() runs first (in run.py), the connection pool tries to log into a database that does not exist yet, causing MySQL to throw error 1049: Unknown database.
Before initializing our global connection pool, we will establish a temporary, raw connection to the MySQL server without specifying a database name. We will use this quick bridge to create glassboard_db. Once the database physically exists, we will spin up the connection pool safely.
'''
def init_pool():
    global _pool
    if _pool is None:
        try:
            #  Connect temporarily to the server without specifying a database
            print("Verifying database container existence...")
            temp_conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD
            )
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB};")
            temp_cursor.close()
            temp_conn.close()
            _pool = MySQLConnectionPool(
                pool_name="glassboard_pool",
                pool_size=Config.MYSQL_POOL_SIZE,  # Pre-allocate (5 default) persistent idle connections in memory
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB
            )
            print("DB pool initialized!")
        except mysql.connector.Error as err:
            print(f"Error in initializing the pool: {err}")
            raise err

def get_db_connection():
    """Fetches an open, active database connection directly from the pool."""
    global _pool
    if _pool is None:
        init_pool()
    return _pool.get_connection()

def execute_schema_file(filepath):
    """Safely opens, parses, and executes an SQL blueprint file line-by-line over a pool connection."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        with open(filepath, 'r') as f:
            schema_text = f.read()
        statements = schema_text.split(';')
        for statement in statements:
            clean_statement = statement.strip()
            if clean_statement:
                cursor.execute(clean_statement)
        conn.commit()
        print("Database architecture successfully constructed.")

    except mysql.connector.Error as err:
        print(f"Failed to execute schema file: {err}")
        raise err

    finally:
        cursor.close()
        conn.close()
