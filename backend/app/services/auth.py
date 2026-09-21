import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# SECRET_KEY signs every token - if this leaks, anyone can forge valid
# tokens for any user. It comes from .env, never hardcoded here.
SECRET_KEY = os.environ["SECRET_KEY"]

# HS256 is a standard, simple choice for signing - one shared secret
# signs and verifies, as opposed to public/private key pairs (which
# you'd want for a system with multiple independent services).
ALGORITHM = "HS256"

# How long a token stays valid after login. 30 minutes is a common
# default; there's no T7+ dependency on this exact number, so it's
# safe to tune later without touching anything else.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# One shared context object. schemes=["bcrypt"] means every hash this
# creates uses bcrypt specifically - deliberately slow, which is what
# makes brute-forcing a stolen hash expensive.
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
    # datetime.now(timezone.utc) instead of the deprecated datetime.utcnow() -
    # utcnow() silently returns a "naive" datetime with no timezone attached,
    # which is a well-known footgun; being explicit about UTC avoids it.
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # "sub" (subject) and "exp" (expiration) are both standard JWT
    # claim names - jose and other JWT libraries know to check "exp"
    # automatically when decoding, so an expired token fails on its own.
    to_encode = {"sub": subject, "exp": expire}

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Verify a token's signature and expiration, and return its subject.

    Returns None if the token is invalid for ANY reason - expired,
    tampered with, signed with a different secret, malformed, etc.
    jose collapses all of these into one JWTError, so we deliberately
    don't distinguish why it failed here - the caller (get_current_user
    in T6's api/deps.py) just needs to know valid vs not.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    return payload.get("sub")