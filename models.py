# ============================================================
# models.py — Database Models (SQLAlchemy ORM)
# ============================================================
# Each class here maps to a PostgreSQL table.
# SQLAlchemy handles creating the tables, inserting rows,
# and querying — you never have to write raw SQL for basic ops.
#
# Tables:
#   users         — registered student accounts
#   notes         — math topic notes (content + metadata)
#   quiz_questions — individual questions belonging to a note
#   read_sessions  — records of when a user read a note
#   quiz_results   — records of completed quiz attempts
#
# To add a new column to a table:
#   1. Add the column attribute here (e.g. db.Column(db.String))
#   2. Run: flask db migrate -m "add column X"
#   3. Run: flask db upgrade
# ============================================================

from datetime import datetime, timezone
from extensions import db   # imported from extensions.py (avoids circular imports)


# ── Helper ────────────────────────────────────────────────────
def utcnow():
    """Returns the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ============================================================
# User — a registered student account
# ============================================================
class User(db.Model):
    __tablename__ = 'users'

    # Primary key — auto-incrementing integer
    id         = db.Column(db.Integer, primary_key=True)

    # The student's display name
    name       = db.Column(db.String(120), nullable=False)

    # Email must be unique across all users
    email      = db.Column(db.String(254), unique=True, nullable=False, index=True)

    # Bcrypt hash of the password — NEVER store the plain-text password
    password_hash = db.Column(db.String(255), nullable=False)

    # When the account was created
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    # ── Relationships ─────────────────────────────────────────
    # These allow us to write user.read_sessions to get all sessions for a user.
    # "cascade delete" means if a user is deleted, their sessions/results go too.
    read_sessions = db.relationship('ReadSession', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    quiz_results  = db.relationship('QuizResult',  backref='user', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        """Serialise to a dict safe to send to the frontend (no password!)."""
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<User {self.email}>'


# ============================================================
# Note — a math topic article
# ============================================================
class Note(db.Model):
    __tablename__ = 'notes'

    # We use the slug string as the primary key (e.g. "quadratic-equations")
    # This matches the id used in your React frontend routes (/notes/:id)
    id         = db.Column(db.String(100), primary_key=True)

    title      = db.Column(db.String(200), nullable=False)

    # Category key (e.g. "ALGEBRA", "GEOMETRY") — matches CATEGORIES in notes.js
    category   = db.Column(db.String(50),  nullable=False)

    # "Foundation", "Core", or "Extended"
    difficulty = db.Column(db.String(20),  nullable=False, default='Core')

    # Estimated reading time in minutes
    read_time  = db.Column(db.Integer, default=5)

    # The full markdown content (can be very long — TEXT has no length limit)
    content    = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # ── Relationships ─────────────────────────────────────────
    quiz_questions = db.relationship('QuizQuestion', backref='note', cascade='all, delete-orphan', lazy='select')
    read_sessions  = db.relationship('ReadSession',  backref='note', cascade='all, delete-orphan', lazy='dynamic')
    quiz_results   = db.relationship('QuizResult',   backref='note', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self, include_content=True):
        """
        Serialise to dict.
        Pass include_content=False for list views (saves bandwidth — don't
        send the full markdown body when only listing notes).
        """
        d = {
            'id':         self.id,
            'title':      self.title,
            'category':   self.category,
            'difficulty': self.difficulty,
            'read_time':  self.read_time,
            'created_at': self.created_at.isoformat(),
        }
        if include_content:
            d['content'] = self.content
        return d

    def __repr__(self):
        return f'<Note {self.id}>'


# ============================================================
# QuizQuestion — a single question for a note's quiz
# ============================================================
class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id      = db.Column(db.Integer, primary_key=True)

    # Foreign key links back to the parent Note
    note_id = db.Column(db.String(100), db.ForeignKey('notes.id'), nullable=False, index=True)

    # The question text (may contain LaTeX: "What is $x^2$?")
    question    = db.Column(db.Text, nullable=False)

    # Store the 4 options as a JSON array — PostgreSQL supports this natively
    # Example: ["Option A", "Option B", "Option C", "Option D"]
    options     = db.Column(db.JSON, nullable=False)

    # Index (0-3) of the correct option in the options array
    correct     = db.Column(db.Integer, nullable=False)

    # Explanation shown after the student answers (may contain LaTeX)
    explanation = db.Column(db.Text, nullable=True)

    # Display order within the quiz
    order       = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id':          self.id,
            'note_id':     self.note_id,
            'question':    self.question,
            'options':     self.options,
            'correct':     self.correct,
            'explanation': self.explanation,
            'order':       self.order,
        }

    def __repr__(self):
        return f'<QuizQuestion {self.id} for {self.note_id}>'


# ============================================================
# ReadSession — records each time a user reads a note
# ============================================================
class ReadSession(db.Model):
    __tablename__ = 'read_sessions'

    id      = db.Column(db.Integer, primary_key=True)

    # Foreign keys — link to User and Note
    user_id = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=False, index=True)
    note_id = db.Column(db.String(100), db.ForeignKey('notes.id'), nullable=False, index=True)

    # When the session was recorded (i.e., when user scrolled 80%+ of the note)
    read_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            'id':         self.id,
            'user_id':    self.user_id,
            'note_id':    self.note_id,
            'note_title': self.note.title if self.note else None,
            'category':   self.note.category if self.note else None,
            'read_at':    self.read_at.isoformat(),
        }

    def __repr__(self):
        return f'<ReadSession user={self.user_id} note={self.note_id}>'


# ============================================================
# QuizResult — records a completed quiz attempt
# ============================================================
class QuizResult(db.Model):
    __tablename__ = 'quiz_results'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=False, index=True)
    note_id    = db.Column(db.String(100), db.ForeignKey('notes.id'), nullable=False, index=True)

    # Number of correct answers
    score      = db.Column(db.Integer, nullable=False)

    # Total number of questions in the quiz
    total      = db.Column(db.Integer, nullable=False)

    # Percentage score (stored redundantly for fast querying)
    percentage = db.Column(db.Integer, nullable=False)

    taken_at   = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            'id':         self.id,
            'user_id':    self.user_id,
            'note_id':    self.note_id,
            'note_title': self.note.title if self.note else None,
            'score':      self.score,
            'total':      self.total,
            'percentage': self.percentage,
            'taken_at':   self.taken_at.isoformat(),
        }

    def __repr__(self):
        return f'<QuizResult user={self.user_id} note={self.note_id} score={self.percentage}%>'
