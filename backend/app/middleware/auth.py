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
    # NOTE: this User lookup runs BEFORE the tenant GUC is set. Under RLS with a
    # non-superuser role we'd need to disable row_security here; on Railway's
    # superuser connection RLS is implicitly bypassed. Filed as follow-up when
    # migrating to a dedicated app role.
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Defence: token's school_id must match the user's persisted school_id.
    # Blocks a forged token that swaps in another school's id — the target
    # school might grant admin, but the forger's user row still belongs to
    # school A.
    if user.school_id != token_school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token school_id does not match user record",
        )

    # Wire tenant isolation: set the DB-level GUC that the RLS policy
    # consults. SET LOCAL means this reverts at transaction end. Every
    # authenticated endpoint downstream now sees only its school's rows.
    db.execute(_sa_text("SET LOCAL app.current_school_id = :sid"),
               {"sid": str(user.school_id)})
    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
