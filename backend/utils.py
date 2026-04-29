import os
import base64
import hashlib
import secrets
import string
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "b27a2885fc06b4c1057899a151d038a48b5f6cc98ae9148d173332579d9383d1")
MASTER_KEY = os.getenv("MASTER_KEY", "938bb2087dfe2adc7729f962e45394c1cf8f9b43025c0f5bbab52b80d2ae1803")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _ks(n):
    k = hashlib.sha256(MASTER_KEY.encode()).digest()
    return (k * (n // len(k) + 1))[:n]

def encrypt_data(s):
    b = s.encode("utf-8")
    return base64.b64encode(bytes(a^c for a,c in zip(b,_ks(len(b))))).decode()

def decrypt_data(s):
    try:
        b = base64.b64decode(s.encode())
        return bytes(a^c for a,c in zip(b,_ks(len(b)))).decode("utf-8")
    except:
        return s

def generate_kod(n=8):
    return ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(n))

def generate_unique_kod(db, model, column, n=8):
    kod = generate_kod(n)
    while db.query(model).filter(column == kod).first():
        kod = generate_kod(n)
    return kod

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_ctx.verify(password, password_hash)

def create_jwt(user_id: int) -> str:
    from jose import jwt
    from datetime import datetime, timedelta
    return jwt.encode(
        {"sub": str(user_id), "exp": datetime.utcnow()+timedelta(days=7)},
        SECRET_KEY,
        algorithm="HS256"
    )

def decode_jwt(token: str) -> dict:
    from jose import jwt
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        return None