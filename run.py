import os
from app.db import init_pool, execute_schema_file


def bootstrap_app():
    """Initializes system resources and verifies database schemas before booting."""
    print("Bootstrapping Glassboard Application Core...")

    # Spin up the thread-safe global connection pool
    init_pool()

    # Locate and execute our physical relational blueprint schema
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'app', 'schema.sql')

    print(f"Loading database blueprint from: {schema_path}")
    execute_schema_file(schema_path)

if __name__ == "__main__":
    bootstrap_app()
    print("Application core is verified and ready for API routes.")