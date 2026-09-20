import cuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
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
    # Login runs BEFORE any tenant identity is known, so a plain
    # db.query(User) would hit RLS with no GUC set and return nothing.
    # find_user_for_login is a SECURITY DEFINER function owned by the
    # superuser that scopes email lookup — the app role can EXECUTE it
    # but can't SELECT the underlying "User" table without a valid
    # tenant GUC. The school_slug filter narrows the lookup inside the
    # function itself; no data leaks that shouldn't.
    school_id_filter: Optional[int] = None
    if form_data.school_slug:
        # School lookup is tenant-agnostic; grants on schools + policy
        # doesn't cover schools (it isn't a tenant table). But we set
        # GUC=0 defensively so no downstream code assumes a real tenant.
        db.execute(text("SET LOCAL app.current_school_id = '0'"))
        school = db.query(School).filter(School.slug == form_data.school_slug).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        school_id_filter = school.id

    rows = db.execute(
        text("SELECT id, email, password, name, role, school_id "
             "FROM find_user_for_login(:email, :school_id)"),
        {"email": form_data.username, "school_id": school_id_filter},
    ).mappings().all()

    candidates = [
        User(
            id=r["id"], email=r["email"], password=r["password"],
            name=r["name"], role=r["role"], school_id=r["school_id"],
        )
        for r in rows
    ]

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
