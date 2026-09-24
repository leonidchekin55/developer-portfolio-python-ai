from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM="HS256"
def hash_password(password:str)->str: return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password:str,hashed:str)->bool:
    try: return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError): return False
def create_token(user_id:int)->str:
    return jwt.encode({"sub":str(user_id),"exp":datetime.now(UTC)+timedelta(hours=8)},settings.secret_key,algorithm=ALGORITHM)
def token_user(token:str)->int:
    try: return int(jwt.decode(token,settings.secret_key,algorithms=[ALGORITHM])["sub"])
    except (JWTError,KeyError,ValueError) as exc: raise ValueError("Invalid token") from exc
