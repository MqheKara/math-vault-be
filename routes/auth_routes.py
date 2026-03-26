# ============================================================
# routes/auth_routes.py — Authentication Endpoints
# ============================================================
# Endpoints:
#   POST /api/auth/register  — create a new student account
#   POST /api/auth/login     — log in and receive a JWT token
#   GET  /api/auth/me        — get the current user's profile
#                              (requires Authorization header with JWT)
#
# How JWT auth works in this app:
#   1. Client POSTs credentials to /login
#   2. Server validates, then returns a signed JWT token string
#   3. Client stores the token (we use localStorage in React)
#   4. Client includes the token in every protected request:
#        Authorization: Bearer <token>
#   5. Server verifies the token on protected routes using
#      the @jwt_required() decorator
# ============================================================

import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from extensions import db
from models import User

# Create a Blueprint — a mini-app that gets registered in app.py
auth_bp = Blueprint('auth', __name__)


# ── POST /api/auth/register ───────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new student account.

    Expected JSON body:
    {
        "name":     "Jane Smith",
        "email":    "jane@example.com",
        "password": "mypassword123"
    }

    Returns:
        201: { "message": "...", "user": {...}, "token": "..." }
        400: { "error": "..." }
    """
    data = request.get_json()

    # ── Validate required fields ──────────────────────────────
    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    name     = (data.get('name')     or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are all required.'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    # ── Check for duplicate email ─────────────────────────────
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists.'}), 400

    # ── Hash the password ─────────────────────────────────────
    # bcrypt.hashpw() returns bytes; we decode to a string for DB storage.
    # The salt is automatically generated and embedded in the hash.
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # ── Create and save the user ──────────────────────────────
    user = User(name=name, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    # ── Issue a JWT token so they're logged in immediately ────
    # The "identity" stored in the token is the user's integer ID.
    # We cast to str because JWT identities must be strings.
    token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Account created successfully.',
        'user':    user.to_dict(),
        'token':   token,
    }), 201


# ── POST /api/auth/login ──────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate an existing user.

    Expected JSON body:
    {
        "email":    "jane@example.com",
        "password": "mypassword123"
    }

    Returns:
        200: { "user": {...}, "token": "..." }
        401: { "error": "..." }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    # ── Look up user ──────────────────────────────────────────
    user = User.query.filter_by(email=email).first()

    # ── Verify password ───────────────────────────────────────
    # bcrypt.checkpw() compares the plain-text attempt against the stored hash.
    # We deliberately give a vague error to not reveal whether the email exists.
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid email or password.'}), 401

    # ── Issue JWT token ───────────────────────────────────────
    token = create_access_token(identity=str(user.id))

    return jsonify({
        'user':  user.to_dict(),
        'token': token,
    }), 200


# ── GET /api/auth/me ──────────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()   # <-- This decorator rejects requests without a valid JWT token
def me():
    """
    Returns the currently authenticated user's profile.
    Used by React on page load to restore login state from a stored token.

    Requires header:
        Authorization: Bearer <token>

    Returns:
        200: { "user": {...} }
        401: handled automatically by Flask-JWT-Extended
    """
    # get_jwt_identity() decodes the token and returns the identity we stored (user ID)
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify({'user': user.to_dict()}), 200
