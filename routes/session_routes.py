# ============================================================
# routes/session_routes.py — Reading Session Endpoints
# ============================================================
# Endpoints:
#   POST /api/sessions/   — record that a user has read a note
#   GET  /api/sessions/   — get all reading sessions for the logged-in user
#
# Both require a valid JWT token (user must be logged in).
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Note, ReadSession

session_bp = Blueprint('sessions', __name__)


# ── POST /api/sessions/ ───────────────────────────────────────
@session_bp.route('/', methods=['POST'])
@jwt_required()
def record_session():
    """
    Records that the logged-in student has read a note.
    Called by NoteReader.jsx when the user scrolls past 80% of the article.
    A new session row is inserted each time (multiple reads are tracked).

    Expected JSON body:
    {
        "note_id": "quadratic-equations"
    }

    Returns:
        201: { "message": "Session recorded.", "session": { ... } }
        400: { "error": "..." }
        404: if the note_id doesn't exist
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    note_id = data.get('note_id')
    if not note_id:
        return jsonify({'error': 'note_id is required.'}), 400

    # Confirm the note exists (returns 404 automatically if not)
    Note.query.get_or_404(note_id, description='Note not found.')

    # Insert a new session record
    session = ReadSession(user_id=user_id, note_id=note_id)
    db.session.add(session)
    db.session.commit()

    return jsonify({
        'message': 'Session recorded.',
        'session': session.to_dict(),
    }), 201


# ── GET /api/sessions/ ────────────────────────────────────────
@session_bp.route('/', methods=['GET'])
@jwt_required()
def get_sessions():
    """
    Returns all reading sessions for the currently logged-in user,
    most recent first. Used by the Dashboard to build the activity timeline.

    Returns:
        200: { "sessions": [ { id, note_id, note_title, category, read_at }, ... ] }
    """
    user_id = int(get_jwt_identity())

    sessions = (
        ReadSession.query
        .filter_by(user_id=user_id)
        .order_by(ReadSession.read_at.desc())
        .all()
    )

    return jsonify({
        'sessions': [s.to_dict() for s in sessions]
    }), 200
