from flask import jsonify


def register_error_handlers(app):
    """Registers global error catches so the API never returns raw HTML crashes."""

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Resource Not Found: The requested endpoint or record does not exist."
        }), 404

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            "error": f"Bad Request: {str(error.description) if hasattr(error, 'description') else 'Malformed request payload.'}"
        }), 400

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({
            "error": "Method Not Allowed: This HTTP action is invalid for the targeted route."
        }), 405

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catches any raw unhandled Python crash and shields the database layout."""
        return jsonify({
            "error": "Internal Server Error: An unexpected issue occurred on the server.",
            "details": str(error)  # Helpful for debugging over PowerShell
        }), 500