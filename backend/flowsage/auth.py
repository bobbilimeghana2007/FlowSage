"""Password hashing (scrypt, stdlib), signed expiring tokens (HMAC-SHA256), rate limiter."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from collections import defaultdict, deque

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
N, R, P = 2 ** 14, 8, 1


class AuthError(Exception):
    pass


def validate_credentials(email: str, password: str) -> None:
    if not isinstance(email, str) or not _EMAIL.match(email) or len(email) > 320:
        raise AuthError("invalid email")
    if not isinstance(password, str) or not (10 <= len(password) <= 128):
        raise AuthError("password must be 10-128 characters")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(secret: str, user_id: str, ttl_s: int, now: float = None) -> str:
    if len(secret) < 16:
        raise AuthError("server secret not configured")
    body = _b64(json.dumps({"sub": user_id, "exp": (now or time.time()) + ttl_s}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(secret: str, token: str, now: float = None) -> str:
    try:
        body, sig = token.split(".")
        good = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            raise AuthError("bad token")
        data = json.loads(_unb64(body))
        if data["exp"] < (now or time.time()):
            raise AuthError("expired token")
        return data["sub"]
    except AuthError:
        raise
    except Exception:
        raise AuthError("bad token")


class RateLimiter:
    def __init__(self, max_events: int, window_s: float):
        self.max, self.window, self.hits = max_events, window_s, defaultdict(deque)

    def allow(self, key: str, now: float = None) -> bool:
        now = now or time.time()
        q = self.hits[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True
