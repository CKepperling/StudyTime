from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Shape of a POST /auth/signup request body."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Shape of a POST /auth/login request body."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Shape of a user as returned by the API.

    Deliberately has NO hashed_password field, unlike the SQLAlchemy
    User model - this is what the outside world is allowed to see.
    """
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Shape of a POST /auth/login response."""
    access_token: str
    token_type: str = "bearer"