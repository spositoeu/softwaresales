# src/auth/jwt.py
import jwt
import datetime

def create_token(user_id, roles):
    """
    Generates a JWT token with user ID and roles.

    Args:
        user_id (int): The ID of the user.
        roles (list): A list of roles for the user.

    Returns:
        str: The JWT token, or None if an error occurs.
    """
    try:
        payload = {
            'user_id': user_id,
            'roles': roles,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)  # Token expiry
        }
        token = jwt.encode(payload, 'your-secret-key', algorithm='HS256')
        return token
    except Exception as e:
        print(f"Error creating token: {e}")
        return None