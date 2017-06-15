import sys, os

# Flask config.py

SQLALCHEMY_DATABASE_URI = os.environ.get('POSTGRES_URL')
