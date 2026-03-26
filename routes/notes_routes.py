# ============================================================
# routes/notes_routes.py — Notes Endpoints
# ============================================================
# Endpoints:
#   GET  /api/notes/           — list all notes (no content, just metadata)
#   GET  /api/notes/<note_id>  — get a single note with full markdown content
#
# Notes are public — no JWT required to read them.
# ============================================================

from flask import Blueprint, jsonify
from models import Note, QuizQuestion

notes_bp = Blueprint('notes', __name__)


# ── GET /api/notes/ ───────────────────────────────────────────
@notes_bp.route('/', methods=['GET'])
def list_notes():
    """
    Returns all notes as a list, WITHOUT the full markdown content.
    This keeps the response small — the homepage only needs titles
    and metadata to render the cards, not the full content.

    Returns:
        200: { "notes": [ { id, title, category, difficulty, read_time }, ... ] }
    """
    # Order alphabetically by title for consistent display
    notes = Note.query.order_by(Note.title).all()
    notecnt = len(notes)

    return jsonify({
        'notes': [note.to_dict(include_content=False) for note in notes],
        'hwmany': str(notecnt)
    }), 200


# ── GET /api/notes/<note_id> ──────────────────────────────────
@notes_bp.route('/<string:note_id>', methods=['GET'])
def get_note(note_id):
    """
    Returns a single note with its FULL markdown content.
    Called when a student navigates to the NoteReader page.

    URL parameter:
        note_id — the string slug, e.g. "quadratic-equations"

    Returns:
        200: { "note": { id, title, category, difficulty, read_time, content } }
        404: { "error": "Note not found." }
    """
    # get_or_404 automatically returns a 404 response if not found
    note = Note.query.get_or_404(note_id, description='Note not found.')
    has_quiz = QuizQuestion.query.filter_by(note_id=note_id).first() is not None
    print(f"Note {note_id} has_quiz={has_quiz}")
    return jsonify({'note': note.to_dict(include_content=True),
                    'has_quiz': has_quiz
                    }), 200
