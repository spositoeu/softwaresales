import jwt
from flask import abort
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

def authenticate_user(email, password):
    """
    Authenticates a user using JWT with Google OAuth2.
    (Placeholder implementation - Replace with actual Google OAuth2 flow)
    """
    # In a real implementation, you would:
    # 1.  Verify the email and password against your database.
    # 2.  If valid, generate a JWT token.

    # Placeholder for JWT generation (replace with your actual implementation)
    # This is just a dummy token for demonstration purposes
    token = jwt.encode({'data': {'email': email, 'user_id': 123}}, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')

    return token

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = None
        # Get token from header
        try:
            token = kwargs.get('Authorization', '').split(' ')[1]
        except IndexError:
            abort(401, 'Token is missing')

        try:
            # Decode JWT
            decoded = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
            # Add decoded data to the request
            # kwargs['user_id'] = decoded['data']['user_id']
        except jwt.ExpiredSignatureError:
            abort(401, 'Token has expired')
        except jwt.InvalidTokenError:
            abort(401, 'Invalid token')

        return func(*args, **kwargs)
    return wrapper