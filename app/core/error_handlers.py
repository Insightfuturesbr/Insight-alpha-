from __future__ import annotations
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "bad_request", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        # Em prod você pode esconder detalhes e logar o traceback
        return jsonify({"error": "internal_server_error"}), 500
