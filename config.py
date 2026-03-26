# ============================================================
# config.py — Application Configuration
# ============================================================
# Reads settings from environment variables (loaded from .env).
# Flask's app.config is populated from whichever Config class
# you pass to create_app().
#
# To add a new config value:
#   1. Add the variable to your .env file
#   2. Read it here with os.environ.get('MY_VAR', 'default')
#   3. Use it in the app as current_app.config['MY_VAR']
# ============================================================

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load variables from the .env file into os.environ
load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    # ── Core Flask ────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # ── Database ──────────────────────────────────────────────
    # SQLAlchemy reads this to know which database to connect to.
    # If DATABASE_URL starts with "postgres://" (older Heroku style),
    # we fix it to "postgresql://" which SQLAlchemy 1.4+ requires.
    _db_url = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:ElPadrino@localhost/mathvault')
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)

    # Disable SQLAlchemy's modification tracking (saves memory, not needed)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT Authentication ────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')

    # How many hours before a token expires and the user must log in again
    _hours = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_hours)

    # ── CORS ──────────────────────────────────────────────────
    # The frontend origin that is allowed to make cross-origin requests.
    CORS_ORIGIN = os.environ.get('CORS_ORIGIN', 'http://localhost:5173')


class DevelopmentConfig(Config):
    """Development-specific overrides."""
    DEBUG = True
    # Echo all SQL queries to the console for debugging
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production-specific overrides."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


# ── Config selector ───────────────────────────────────────────
# Maps the FLASK_ENV string to the right config class.
config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
}

def get_config():
    """Returns the right Config class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
