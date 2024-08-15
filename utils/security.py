import logging
import os
import secrets
import hashlib
import base64
import jwt
import secrets

from datetime import datetime, timedelta
from fastapi import HTTPException, logger
from dotenv import load_dotenv
from jwt import PyJWTError
from functools import wraps

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")

#encriptaciones


def generate_pkce_verifier():
    return secrets.token_urlsafe(32)

def generate_pkce_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


def create_jwt_token(email: str, active: int):
    logger.info(f"Tercera parada - Iniciando creación del JWT para el email: {email}")
    expiration = datetime.utcnow() + timedelta(hours=1)  # El token expira en 1 hora
    logger.info(f"Cuarta parada - Expiración del token: {expiration}")

    try:
        token = jwt.encode(
            {
                "email": email,
                "exp": expiration,
                "active": active,
                "iat": datetime.utcnow()
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        logger.info(f"Secret_key es: {SECRET_KEY}")
        return token
    except Exception as e:
        logger.error(f"Error creando el token JWT: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creando el token JWT")


# Crear un decorador para validar el JWT
def validate(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request:
            raise HTTPException(status_code=400, detail="Request object not found")

        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=403, detail="Authorization header missing")

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme")

            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

            email = payload.get("email")
            expired = payload.get("exp")
            active = payload.get("active")
            if email is None or expired is None or active is None:
                raise HTTPException(status_code=403, detail="Invalid token")

            if datetime.utcfromtimestamp(expired) < datetime.utcnow():
                raise HTTPException(status_code=403, detail="Expired token")

            if not active:
                raise HTTPException(status_code=403, detail="Inactive user")

            # Inyectar el email en el objeto request
            request.state.email = email
        except PyJWTError:
            raise HTTPException(status_code=403, detail="Invalid token or expired token")

        return await func(*args, **kwargs)
    return wrapper