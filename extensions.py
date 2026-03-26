# ============================================================
# extensions.py — Shared Flask Extension Instances
# ============================================================
# We instantiate all Flask extensions here WITHOUT passing the
# app object yet. The actual binding happens inside create_app()
# in app.py via the .init_app(app) pattern.
#
# Why this file exists:
#   If we created db = SQLAlchemy(app) inside app.py, and then
#   models.py imported from app.py, and app.py imported models.py,
#   we'd have a circular import error. By putting extensions here,
#   models.py can safely import db from extensions without
#   touching app.py at all.
# ============================================================

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# ORM — maps Python classes to PostgreSQL tables
db = SQLAlchemy()

# Migrations — handles ALTER TABLE etc. when models change
migrate = Migrate()

# JWT — handles creating and verifying auth tokens
jwt = JWTManager()

# CORS — allows the React app on localhost:5173 to call this API
cors = CORS()
