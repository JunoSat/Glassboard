import os
from app import create_app
from app.models import db

app = create_app()

# Auto-create tables if database file doesn't exist (useful for quick start without seeding)
with app.app_context():
    # If using SQLite, we can inspect if we need to create
    db.create_all()

if __name__ == '__main__':
    # Default Flask port is 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
