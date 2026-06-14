from flask import request, jsonify
from functools import wraps
import jwt
from app.config import Config


# This is our custom security wrapper
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 1. Look inside the HTTP request headers for an 'Authorization' rule
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            # Headers usually look like: "Bearer abc123xyz_token_string"
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]  # Grab just the token string

        # 2. If the user didn't send a token, block them immediately
        if not token:
            return jsonify({"error": "Access Denied: Missing token."}), 401

        try:
            # 3. Ask the JWT library to decode and verify the signature using our SECRET_KEY
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])

            # 4. If the signature matches, extract the user data packed inside it
            current_user = {
                "id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role")
            }
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."}), 401

        # 5. Pass the verified current_user info into the actual endpoint function
        return f(current_user, *args, **kwargs)

    return decorated


def roles_allowed(*roles):
    """Enforces Role-Based Access Control (RBAC) by checking tiered user roles."""
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            # Check if the user's role matches the allowed tier
            if current_user["role"] not in roles:
                return jsonify({
                    "error": f"Forbidden: Role '{current_user['role']}' does not have permission."
                }), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator