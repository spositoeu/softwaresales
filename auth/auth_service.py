# auth/auth_service.py
import jwt
from datetime import datetime, timedelta
from itsdangerous import CompactSerializers, BadSignatureError

class JWTService:
    def __init__(self, secret_key, issuer="SoftwareSales"):
        self.secret_key = secret_key
        self.issuer = issuer
        self.serializer = CompactSerializers(secret_key=self.secret_key, issuers=[self.issuer])

    def generate_token(self, user_id):
        payload = {
            'sub': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = self.serializer.dumps(payload)
        return token

    def verify_token(self, token):
        try:
            payload = self.serializer.loads(token)
            return payload
        except BadSignatureError:
            return None