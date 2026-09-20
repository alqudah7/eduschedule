import cuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_password, create_access_token, get_current_user
from app.models.teacher import User
from app.models.tenant import School

router = APIRouter()


class _LoginForm(OAuth2PasswordRequestForm):
    """Extends OAuth2PasswordRequestForm with an optional school_slug.

    Once multi-school is in production a client can identify which
    tenant to authenticate against; single-tenant deployments continue
    to work because we still fall back to looking up the user by email
    when no slug is supplied AND exactly one match exists.
    """
    def __init__(
        self,
        username: str = Form(...),
        password: str = Form(...),
        school_slug: Optional[str] = Form(None),
        grant_type: Optional[str] = Form(None),
        scope: str = Form(""),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ):
        super().__init__(
            grant_type=grant_type, username=username, password=password,
            scope=scope, client_id=client_id, client_secret=client_secret,
        )
        self.school_slug = school_slug


@router.post("/login")
def login(form_data: _LoginForm = Depends(), db: Session = Depends(get_db)):
    """Log in and return a JWT that carries the user's school_id claim.

    Lookup logic:
    - If school_slug provided: scope to that school directly.
    - Otherwise: find users matching the email; if exactly one match,
      log them in. If multiple matches (same email at more than one
      school), require a school_slug — do not guess.
    """
    q = db.query(User).filter(User.email == form_data.username)
    if form_data.school_slug:
        school = db.query(School).filter(School.slug == form_data.school_slug).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        q = q.filter(User.school_id == school.id)

    candidates = q.all()
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if len(candidates) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email exists at multiple schools; include school_slug",
        )

    user = candidates[0]
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "school_id": user.school_id,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "school_id": user.school_id,
        },
    }


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
    }
