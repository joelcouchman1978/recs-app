from typing import Optional
import os, json, hmac, hashlib, base64


def _b64url_decode(s: str) -> bytes:
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def parse_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = authorization
    if token.startswith("devtoken:"):
        return token.split(":", 1)[1]
    # Optionally accept a JWT (HS256) when JWT_SECRET is set
    secret = os.getenv("JWT_SECRET")
    if secret and token.count('.') == 2:
        try:
            header_b64, payload_b64, sig_b64 = token.split('.')
            header = json.loads(_b64url_decode(header_b64))
            if header.get('alg') != 'HS256':
                return None
            signing_input = f"{header_b64}.{payload_b64}".encode()
            expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
            actual = _b64url_decode(sig_b64)
            if not hmac.compare_digest(expected, actual):
                return None
            payload = json.loads(_b64url_decode(payload_b64))
            email = payload.get('email') or payload.get('sub')
            if isinstance(email, str) and email:
                return email
        except Exception:
            return None
    return None
