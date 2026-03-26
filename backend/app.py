"""
Flask app factory — punto de entrada del backend.
Sirve la API y el frontend React (build estático).
"""

import os
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from backend.config import FRONTEND_DIST


def create_app():
    app = Flask(__name__, static_folder=None)
    CORS(app)

    # ── Registrar blueprints ──
    from backend.routes.pairing import pairing_bp
    from backend.routes.cropping import cropping_bp
    from backend.routes.folders import folders_bp
    from backend.routes.upload import upload_bp
    from backend.routes.video_extraction import video_bp
    from backend.routes.labeling import labeling_bp
    from backend.routes.testing import testing_bp

    app.register_blueprint(pairing_bp)
    app.register_blueprint(cropping_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(labeling_bp)
    app.register_blueprint(testing_bp)

    # ── Servir React SPA ──
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_spa(path):
        """
        Sirve archivos estáticos del build de React.
        Para cualquier ruta que no sea un archivo real, devuelve index.html
        para que React Router maneje la navegación.
        """
        index_path = os.path.join(FRONTEND_DIST, 'index.html')

        if path and path.startswith('api/'):
            # No debería llegar aquí, pero por seguridad
            return 'Not found', 404

        if path:
            file_path = os.path.join(FRONTEND_DIST, path)
            if os.path.isfile(file_path):
                return send_from_directory(FRONTEND_DIST, path)

        # Fallback: servir index.html para React Router
        if os.path.isfile(index_path):
            return send_file(index_path)

        return ('<h1>Frontend no compilado</h1>'
                '<p>Ejecuta <code>cd frontend && npm run build</code></p>'), 503

    return app
