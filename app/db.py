import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from app.config import Config

_pool = None # This variable will store the connection pool decrlaring before to later check status

def init_pool():
    global _pool
    if _pool is None:
        try:
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
