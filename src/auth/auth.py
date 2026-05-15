# src/auth/auth.py
import jwt
from datetime import datetime, timedelta

JWT_SECRET = "your-secret-key"  # Replace with a strong, secure secret key

def verify_jwt(token):
    """
    Verifies a JWT token and returns the user ID and role if valid.
    Handles invalid or expired tokens.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        role = payload.get("role")

        if user_id is None or role is None:
            raise jwt.ExpiredSignatureError("Missing user_id or role in JWT")

        return user_id, role

    except jwt.ExpiredSignatureError:
        raise  # Re-raise the exception to be handled by the caller
    except jwt.InvalidTokenError:
        raise  # Re-raise the exception to be handled by the caller
    except Exception as e:
        print(f"Error verifying JWT: {e}")
        return None, None