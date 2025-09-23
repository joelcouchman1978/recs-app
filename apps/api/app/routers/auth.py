import os, json, base64, hmac, hashlib, time
from fastapi import APIRouter
from .utils import parse_token
from ..schemas import MagicLinkRequest, MagicLinkResponse

router = APIRouter()


@router.post("/auth/magic", response_model=MagicLinkResponse)
def auth_magic(payload: MagicLinkRequest):
    token = f"devtoken:{payload.email}"
    return MagicLinkResponse(token=token)


@router.post("/auth/login", response_model=MagicLinkResponse)
def auth_login(payload: MagicLinkRequest):
    secret = os.getenv("JWT_SECRET")
    if not secret:
        return MagicLinkResponse(token=f"devtoken:{payload.email}")
    header = {"alg":"HS256","typ":"JWT"}
    now = int(time.time())
    body = {"email": payload.email, "iat": now, "exp": now + 60*60*8}
    def b64url(d: bytes) -> str:
        return base64.urlsafe_b64encode(d).decode().rstrip('=')
    header_b64 = b64url(json.dumps(header, separators=(',',':')).encode())
    body_b64 = b64url(json.dumps(body, separators=(',',':')).encode())
    signing_input = f"{header_b64}.{body_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    token = f"{header_b64}.{body_b64}.{b64url(sig)}"
    return MagicLinkResponse(token=token)
