"""Registration and login API routes for ChronosMatch."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .auth import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)
from .user_repository import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    email = payload.get("sub")

    user = get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(request: RegisterRequest):
    email = request.email.strip().lower()
    username = request.username.strip()

    if (
        not username
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid username and email address",
        )

    if get_user_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    try:
        hashed_password = hash_password(request.password)

        user = create_user(
            username=username,
            email=email,
            password_hash=hashed_password,
        )

    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Username or email is already registered",
        ) from exc

    return {
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }


@router.post(
    "/login",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "password": {"type": "string"},
                        },
                        "required": ["email", "password"],
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                        },
                        "required": ["username", "password"],
                    }
                },
            },
        }
    },
)
async def login_user(request: Request):
    """Accept both Swagger form data and JSON login requests."""

    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        email = str(form_data.get("username", ""))
        password = str(form_data.get("password", ""))
    else:
        try:
            data = await request.json()
            email = str(data.get("email", ""))
            password = str(data.get("password", ""))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid login request",
            )

    email = email.strip().lower()
    user = get_user_by_email(email)

    if user is None or not verify_password(
        password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_my_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }