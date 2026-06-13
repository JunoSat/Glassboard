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