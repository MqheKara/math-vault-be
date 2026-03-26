# ============================================================
# app.py — Flask Application Factory
# ============================================================
# Uses the "application factory" pattern: create_app() builds
# and returns the Flask app. This makes it easy to create
# test instances with different configs.
#
# Run the dev server with:
#   python app.py
#   — or —
#   flask run
# ============================================================

from flask import Flask
from flask_restful import Api

from config import get_config
from extensions import db, migrate, jwt, cors

# Import all route blueprints / resource modules
# (these register the URL endpoints)
from routes.auth_routes    import auth_bp
from routes.notes_routes   import notes_bp
from routes.quiz_routes    import quiz_bp
from routes.session_routes import session_bp
from routes.dashboard_routes import dashboard_bp


def create_app():
    """
    Application factory.
    Creates a configured Flask app with all extensions and routes registered.
    """
    app = Flask(__name__)

    # ── Load configuration ────────────────────────────────────
    app.config.from_object(get_config())

    # ── Initialise extensions with the app ───────────────────
    # Each .init_app() call binds the extension to this specific app instance.
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # CORS: allow requests from the React frontend origin
    cors.init_app(app, resources={
        r'/api/*': {
            'origins': app.config['CORS_ORIGIN'],
            # Allow these headers so JWT tokens can be sent
            'allow_headers': ['Content-Type', 'Authorization'],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        }
    })

    # ── Register route blueprints ─────────────────────────────
    # All our API routes live under the /api prefix.
    # The url_prefix here is combined with the prefix in each blueprint.
    #
    # Final URL examples:
    #   POST /api/auth/register
    #   POST /api/auth/login
    #   GET  /api/notes/
    #   GET  /api/notes/quadratic-equations
    #   GET  /api/quiz/quadratic-equations
    #   POST /api/sessions/
    #   POST /api/quiz-results/
    #   GET  /api/dashboard/summary

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(notes_bp,     url_prefix='/api/notes')
    app.register_blueprint(quiz_bp,      url_prefix='/api/quiz')
    app.register_blueprint(session_bp,   url_prefix='/api/sessions')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    # ── Health check endpoint ─────────────────────────────────
    # Useful for confirming the server is running.
    # Visit: GET http://localhost:5000/api/health
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'MathVault API is running'}

    # ── JWT error handlers ────────────────────────────────────
    # These return clean JSON instead of HTML error pages when tokens are bad.

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired. Please log in again.'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid authentication token.'}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authentication required. Please log in.'}, 401

    return app


# ── Entry point ───────────────────────────────────────────────
# Running `python app.py` directly starts the dev server.
if __name__ == '__main__':
    app = create_app()
    # debug=True enables auto-reload when you save a file
    app.run(host='0.0.0.0', debug=True, port=5000)
