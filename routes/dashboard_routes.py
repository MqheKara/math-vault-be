# ============================================================
# routes/dashboard_routes.py — Dashboard Aggregation Endpoint
# ============================================================
# Endpoint:
#   GET /api/dashboard/summary — returns all stats needed by
#                                the Dashboard page in one request
#
# This single endpoint replaces four separate calls, keeping
# the frontend simple and reducing network round-trips.
# ============================================================

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from extensions import db
from models import User, ReadSession, QuizResult

from flask import Blueprint
dashboard_bp = Blueprint('dashboard', __name__)


# ── GET /api/dashboard/summary ────────────────────────────────
@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary():
    """
    Returns everything the Dashboard page needs in a single response:

    {
      "user": { id, name, email, created_at },

      "stats": {
        "notes_read":     <number of distinct notes read>,
        "total_reads":    <total read sessions>,
        "quizzes_taken":  <total quiz attempts>,
        "avg_quiz_score": <average percentage across all attempts>
      },

      "reading_summary": {
        "<note_id>": {
          "title":       "...",
          "category":    "ALGEBRA",
          "count":       3,
          "last_read_at": "2024-..."
        },
        ...
      },

      "quiz_summary": {
        "<note_id>": {
          "title":            "...",
          "best_percentage":  90,
          "best_score":       9,
          "total":            10,
          "attempts":         2
        },
        ...
      },

      "recent_sessions": [
        { id, note_id, note_title, category, read_at },
        ...  (last 20, most recent first)
      ]
    }
    """
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)

    # ── Reading Summary ───────────────────────────────────────
    # Use a GROUP BY query to count sessions per note efficiently.
    # This is much faster than loading all sessions into Python and grouping there.
    reading_rows = (
        db.session.query(
            ReadSession.note_id,
            func.count(ReadSession.id).label('count'),
            func.max(ReadSession.read_at).label('last_read_at'),
        )
        .filter(ReadSession.user_id == user_id)
        .group_by(ReadSession.note_id)
        .all()
    )

    # Build a dict keyed by note_id
    # We need to join note titles — fetch the notes for these IDs
    from models import Note
    note_ids = [row.note_id for row in reading_rows]
    notes_map = {n.id: n for n in Note.query.filter(Note.id.in_(note_ids)).all()} if note_ids else {}
    totalNotes = db.session.query(func.count(Note.id)).scalar()
    reading_summary = {}
    for row in reading_rows:
        note = notes_map.get(row.note_id)
        reading_summary[row.note_id] = {
            'title':        note.title    if note else row.note_id,
            'category':     note.category if note else '',
            'count':        row.count,
            'last_read_at': row.last_read_at.isoformat() if row.last_read_at else None,
        }

    # ── Quiz Summary ──────────────────────────────────────────
    # For each note, find the best percentage score and count of attempts.
    quiz_rows = (
        db.session.query(
            QuizResult.note_id,
            func.count(QuizResult.id).label('attempts'),
            func.max(QuizResult.percentage).label('best_percentage'),
        )
        .filter(QuizResult.user_id == user_id)
        .group_by(QuizResult.note_id)
        .all()
    )

    quiz_note_ids = [row.note_id for row in quiz_rows]
    quiz_notes_map = {n.id: n for n in Note.query.filter(Note.id.in_(quiz_note_ids)).all()} if quiz_note_ids else {}

    # For each note, also fetch the actual score/total from the best attempt
    quiz_summary = {}
    for row in quiz_rows:
        note = quiz_notes_map.get(row.note_id)

        # Get the best-scoring result row (to retrieve score and total)
        best = (
            QuizResult.query
            .filter_by(user_id=user_id, note_id=row.note_id, percentage=row.best_percentage)
            .order_by(QuizResult.taken_at.desc())
            .first()
        )

        quiz_summary[row.note_id] = {
            'title':           note.title if note else row.note_id,
            'best_percentage': row.best_percentage,
            'best_score':      best.score if best else 0,
            'total':           best.total if best else 0,
            'attempts':        row.attempts,
        }

    # ── Aggregate Stats ───────────────────────────────────────
    total_reads   = sum(v['count'] for v in reading_summary.values())
    notes_read    = len(reading_summary)
    quizzes_taken = sum(v['attempts'] for v in quiz_summary.values())

    # Average quiz score across all attempts (not just best)
    all_results = QuizResult.query.filter_by(user_id=user_id).all()
    avg_score   = round(sum(r.percentage for r in all_results) / len(all_results)) if all_results else 0

    # ── Recent Sessions (timeline) ────────────────────────────
    recent = (
        ReadSession.query
        .filter_by(user_id=user_id)
        .order_by(ReadSession.read_at.desc())
        .limit(20)
        .all()
    )

    return jsonify({
        'user': user.to_dict(),

        'stats': {
            'notes_read':     notes_read,
            'total_reads':    total_reads,
            'quizzes_taken':  quizzes_taken,
            'avg_quiz_score': avg_score,
        },

        'reading_summary': reading_summary,
        'quiz_summary':    quiz_summary,
        'total_notes': totalNotes,
        'recent_sessions': [s.to_dict() for s in recent],
    }), 200
