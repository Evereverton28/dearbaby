from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.models.user import User
from app.schemas.auth import (
    SignupRequest, TokenResponse, UserResponse,
    SocialLoginRequest, PasswordResetRequest,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _tokens(user.id)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(),
          session: Session = Depends(get_session)):
    # OAuth2PasswordRequestForm uses 'username' — we treat it as the email.
    user = session.exec(select(User).where(User.email == form.username)).first()
    if not user or not user.password_hash or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _tokens(user.id)


@router.post("/social", response_model=TokenResponse)
def social_login(body: SocialLoginRequest, session: Session = Depends(get_session)):
    """
    Google/Apple login. In production, VERIFY body.id_token against the provider's
    public certs (google-auth / apple's JWKS) and extract the email + subject.
    Below is the account-linking logic once the token is verified.
    """
    # --- placeholder for verified claims (replace with real verification) ---
    verified_email = None   # e.g. claims["email"]
    verified_sub = None     # e.g. claims["sub"]
    if not verified_email:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED,
                            "Wire up provider token verification (see docstring)")

    user = session.exec(select(User).where(User.email == verified_email)).first()
    if not user:
        user = User(email=verified_email, display_name=verified_email.split("@")[0],
                    provider=body.provider, provider_uid=verified_sub,
                    email_verified=True)
        session.add(user)
        session.commit()
        session.refresh(user)
    return _tokens(user.id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_token: str, session: Session = Depends(get_session)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = session.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _tokens(user.id)


@router.post("/password-reset", status_code=202)
def password_reset(body: PasswordResetRequest):
    """
    Always returns 202 whether or not the email exists (don't leak which emails
    are registered). A background job emails a signed, single-use reset link.
    """
    return {"detail": "If that email exists, a reset link has been sent."}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
