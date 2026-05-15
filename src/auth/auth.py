from functools import wraps
from jwt import JWTError
from flask import request, jsonify
import os
import uuid
from datetime import datetime

# Replace with your Google Cloud Project ID
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.environ.get("JWT_SECRET", "YOUR_JWT_SECRET")
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", 30))

class User:
    def __init__(self, user_id, email, username):
        self.user_id = user_id
        self.email = email
        self.username = username

def generate_jwt(user):
    payload = {
        'user_id': user.user_id,
        'email': user.email,
        'username': user.username,
        'exp': datetime.utcnow() + JWT_EXPIRATION_MINUTES * datetime.timedelta(minutes=1)
    }
    return JWT.encode(payload, JWT_SECRET)

class JWT:
    def encode(payload, secret):
        import jwt
        return jwt.encode(payload, secret, algorithm='HS256')

    @staticmethod
    def decode(token, secret):
        import jwt
        try:
            decoded = jwt.decode(token, secret, algorithms=['HS256'])
            return decoded
        except JWTError as e:
            print(e)
            return None

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Authorization header missing'}), 401

        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'message': 'Invalid Authorization header format'}), 401

        decoded = JWT.decode(token, JWT_SECRET)
        if decoded:
            return func(*args, **kwargs, jwt_payload=decoded)
        else:
            return jsonify({'message': 'Invalid JWT token'}), 401
    return wrapper