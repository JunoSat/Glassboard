import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'glassboard-secret-key-12345')
    
    # Defaults to local SQLite, but can be easily overridden via DATABASE_URL env var (e.g., MySQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'glassboard.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-54321')
    # Let tokens last 12 hours for testing and local usage convenience
    JWT_ACCESS_TOKEN_EXPIRES = 43200
