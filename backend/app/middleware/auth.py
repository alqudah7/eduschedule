from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


_JWT_ALGORITHM = "HS256"  # hardcoded — env var parsing on Render can corrupt this value


def create_access_token(data: dict) -> str:
    """Encode a JWT.

    Callers MUST include `sub` (user id) and `school_id` at minimum.
    `school_id` is the ONLY source of tenant identity for the request:
    it must never be derived from a query param, path segment, or
    header at any downstream layer (MULTITENANT.md §6 layer 3).
    """
    to_encode = data.copy()
    if "school_id" not in to_encode:
        raise RuntimeError(
            "create_access_token: school_id claim is required for tenant isolation"
        )
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    token_school_id = payload.get("school_id")
    if token_school_id is None:
        # Pre-multitenant token (issued before Phase 1). Force re-login.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing school_id claim — please log in again",
        )
    from app.models.teacher import User
    from sqlalchemy import text as _sa_text
    # Set the tenant GUC FIRST — the User query below runs under RLS
    # (app connects as a non-superuser role) so without the GUC it
    # would return zero rows and the request would 401 with "User not
    # found" even for a valid token. token_school_id is user-controlled
    # but the next check catches forgery: if the User row's school_id
    # does not match, we 403.
    db.execute(_sa_text("SET LOCAL app.current_school_id = :sid"),
               {"sid": str(token_school_id)})

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Defence: token's school_id must match the user's persisted school_id.
    # Blocks a forged token that swaps in another school's id — the target
    # school might grant admin, but the forger's user row still belongs to
    # school A. The GUC we just set is what RLS uses; if the token forged a
    # different school_id, the lookup either returns nothing (user's real
    # school_id != GUC, RLS blocks the row) or returns the row and this
    # equality check fails.
    if user.school_id != token_school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token school_id does not match user record",
        )
    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_current_password(current_user=Depends(get_current_user)):
    """Block every endpoint until the user has rotated a default password.

    Applied globally as a middleware. The login and change-password
    endpoints skip this check by taking `get_current_user` directly.
    Everywhere else, if `User.must_change_password` is TRUE, the API
    returns 428 Precondition Required with a header telling the client
    which endpoint to route to. Frontend hiding the UI is not enough —
    a hostile client that skips the redirect must still be blocked.
    """
    if getattr(current_user, "must_change_password", False):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="password_change_required",
            headers={"X-Password-Change-Required": "true",
                     "X-Password-Change-Endpoint": "/api/auth/change-password"},
        )
    return current_user
