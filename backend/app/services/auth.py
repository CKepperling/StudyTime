import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ["SECRET_KEY"]

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Turn a raw password into a bcrypt hash for storing in the DB.

    Called once, at signup. The raw password itself is never stored -
    only this hash is.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt's raw password against the stored hash.

    This does NOT reverse the hash to get the original password back
    (bcrypt hashes can't be reversed) - it re-hashes plain_password
    the same way and checks if the result matches.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """Build a signed JWT for a logged-in user.

    subject is "who this token is for" - by convention this is the
    user's id or email, stored in the JWT's standard "sub" claim.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"sub": subject, "exp": expire}

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Verify a token's signature and expiration, and return its subject.

    Returns None if the token is invalid for ANY reason - expired,
    tampered with, signed with a different secret, malformed, etc.
    jose collapses all of these into one JWTError, so we deliberately
    don't distinguish why it failed here.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    return payload.get("sub")