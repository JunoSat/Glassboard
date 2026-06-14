import os

class Config:
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'glassboard_db')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'your_fallback_password_here') # change accordingly
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-super-secret-development-key-change-in-production')

    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE', 5))


 # set MYSQL_PASSWORD=your_actual_mysql_password_here in cmd windows
 # export MYSQL_PASSWORD="your_actual_mysql_password_here" for linux/mac bash/zsh