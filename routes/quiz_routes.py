# ============================================================
# routes/quiz_routes.py — Quiz Endpoints
# ============================================================
# Endpoints:
#   GET  /api/quiz/<note_id>   — get all questions for a note's quiz
#   POST /api/quiz/results     — save a completed quiz attempt
#
# Both endpoints require the user to be logged in (JWT required).
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Note, QuizQuestion, QuizResult

quiz_bp = Blueprint('quiz', __name__)


# ── GET /api/quiz/<note_id> ───────────────────────────────────
@quiz_bp.route('/<string:note_id>', methods=['GET'])
@jwt_required()
def get_quiz(note_id):
    """
    Returns all quiz questions for a given note, ordered by their
    'order' field. Login required so only registered students can
    access quizzes.

    URL parameter:
        note_id — e.g. "quadratic-equations"

    Returns:
        200: {
               "note_id":    "quadratic-equations",
               "note_title": "Quadratic Equations",
               "questions":  [ { id, question, options, correct, explanation, order }, ... ]
             }
        404: { "error": "Note not found." }
        404: { "error": "No quiz found for this note." }
    """
    # Confirm the note exists
    note = Note.query.get_or_404(note_id, description='Note not found.')

    # Get questions sorted by their display order
    questions = (
        QuizQuestion.query
        .filter_by(note_id=note_id)
        .order_by(QuizQuestion.order)
        .all()
    )

    if not questions:
        return jsonify({'error': 'No quiz found for this note.'}), 404

    return jsonify({
        'note_id':    note.id,
        'note_title': note.title,
        'questions':  [q.to_dict() for q in questions],
    }), 200


# ── POST /api/quiz/results ────────────────────────────────────
@quiz_bp.route('/results', methods=['POST'])
@jwt_required()
def save_quiz_result():
    """
    Saves a completed quiz attempt to the database.
    Called automatically by QuizPage.jsx when the student finishes.

    Expected JSON body:
    {
        "note_id": "quadratic-equations",
        "score":   4,
        "total":   5
    }

    Returns:
        201: { "message": "Result saved.", "result": { ... } }
        400: { "error": "..." }
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    note_id = data.get('note_id')
    score   = data.get('score')
    total   = data.get('total')

    # Validate all required fields are present
    if note_id is None or score is None or total is None:
        return jsonify({'error': 'note_id, score, and total are all required.'}), 400

    if total <= 0:
        return jsonify({'error': 'total must be greater than 0.'}), 400

    # Confirm the note exists
    Note.query.get_or_404(note_id, description='Note not found.')

    # Calculate the percentage
    percentage = round((score / total) * 100)

    # Create and persist the result record
    result = QuizResult(
        user_id    = user_id,
        note_id    = note_id,
        score      = score,
        total      = total,
        percentage = percentage,
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        'message': 'Result saved.',
        'result':  result.to_dict(),
    }), 201
