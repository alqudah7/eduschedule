from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import (
    verify_password, hash_password, create_access_token, get_current_user,
)
from app.models.teacher import User

router = APIRouter()


# Minimum acceptable password. This is deliberately modest — the point
# of the forced-change flow is to STOP shared default passwords being
# reused, not to enforce a security theatre policy. If we ever want
# strength scoring, wire zxcvbn in here.
_MIN_PASSWORD_LEN = 10


# ── Server-resolved tenant ────────────────────────────────────────────────
#
# Until Phase 3 (subdomain routing) lands, we do NOT accept a school_slug or
# any other tenant identifier from the login request — that was previously a
# cross-tenant authentication and user-enumeration vector. The tenant is
# resolved server-side to the single production school (Al Hekma, id=1).
#
# When Phase 3 arrives, replace this constant with a resolver that reads the
# request's Host header / subdomain, maps it to a schools row, and rejects
# unknown hosts before password verification runs.
_LOGIN_SCHOOL_ID = 1


# ── Constant-time timing dummy ───────────────────────────────────────────
#
# Login must take the same amount of time whether or not the email exists.
# bcrypt (via passlib) is ~100 ms per verify. If we short-circuit on
# "no such user" we leak the existence of an email via response timing.
# _DUMMY_HASH is bcrypt of a value the client cannot produce; verifying
# against it always returns False and takes the same time as a real check.
_DUMMY_HASH = hash_password("this-hash-only-exists-to-normalise-login-timing")


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate and return a JWT that carries the user's school_id.

    Hardening notes:
      - Tenant is server-resolved (see _LOGIN_SCHOOL_ID). The client cannot
        influence which school it authenticates against.
      - The pre-auth User lookup goes through find_user_for_login — a
        SECURITY DEFINER function owned by the superuser — because the app
        role cannot SELECT "User" directly (RLS with app.current_school_id
        unset returns zero rows).
      - Response shape and timing are identical for every failure mode
        ("no such user", "wrong password", "wrong tenant"). Attackers
        cannot enumerate emails via the response.
    """
    row = db.execute(
        text("SELECT id, email, password, name, role, school_id, "
             "must_change_password "
             "FROM find_user_for_login(:email, :school_id)"),
        {"email": form_data.username, "school_id": _LOGIN_SCHOOL_ID},
    ).mappings().first()

    stored_hash = row["password"] if row else _DUMMY_HASH
    password_ok = verify_password(form_data.password, stored_hash)

    if not row or not password_ok:
        # Same status, same body, same latency in every failure branch.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({
        "sub": row["id"],
        "email": row["email"],
        "role": row["role"],
        "school_id": row["school_id"],
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": bool(row["must_change_password"]),
        "user": {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "school_id": row["school_id"],
            "must_change_password": bool(row["must_change_password"]),
        },
    }


class _ChangePasswordBody(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=_MIN_PASSWORD_LEN)


@router.post("/change-password")
def change_password(
    body: _ChangePasswordBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a new password and clear must_change_password.

    Requires the current password so a stolen token cannot rotate the
    password of a user who has walked away from a terminal. Rejects
    a "new" that is byte-for-byte equal to "current" so users can't
    trivially defeat a forced change.
    """
    if not verify_password(body.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    current_user.password = hash_password(body.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()

    return {"message": "Password updated"}


@router.post("/logout")
def logout():
    return {"message": "Logged out"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "school_id": current_user.school_id,
        "must_change_password": current_user.must_change_password,
    }
