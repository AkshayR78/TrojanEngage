import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import Literal

_BASE64URL_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+$")
_TOKEN_TTL_SECONDS = 3600


def validate_jwt_secret(secret: str) -> None:
    if len(secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")


class TokenError(ValueError):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    subject: str
    role: Literal["student", "org"]


def create_demo_student_identity() -> str:
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


def create_access_token(
    subject: str,
    role: Literal["student", "org"],
    secret: str,
) -> str:
    header = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = _encode_segment(
        {
            "sub": subject,
            "role": role,
            "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
        }
    )
    signing_input = f"{header}.{payload}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256)
    return f"{signing_input}.{_encode_bytes(signature.digest())}"


def decode_access_token(token: str, secret: str) -> AccessTokenClaims:
    if len(token) > 4096:
        raise TokenError("Invalid access token")

    segments = token.split(".")
    if len(segments) != 3:
        raise TokenError("Invalid access token")

    header_segment, payload_segment, signature_segment = segments
    header = _decode_segment(header_segment)
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise TokenError("Invalid access token")

    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    supplied_signature = _decode_bytes(signature_segment)
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise TokenError("Invalid access token")

    payload = _decode_segment(payload_segment)
    if not isinstance(payload, dict):
        raise TokenError("Invalid access token")

    subject = payload.get("sub")
    role = payload.get("role")
    expires_at = payload.get("exp")
    if (
        not isinstance(subject, str)
        or not subject
        or role not in ("student", "org")
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
        or expires_at <= int(time.time())
    ):
        raise TokenError("Invalid or expired access token")

    return AccessTokenClaims(subject=subject, role=role)


def _encode_segment(value: dict[str, str | int]) -> str:
    return _encode_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_segment(segment: str) -> object:
    if not _BASE64URL_SEGMENT.fullmatch(segment):
        raise TokenError("Invalid access token")
    try:
        decoded = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        return json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TokenError("Invalid access token") from exc


def _decode_bytes(segment: str) -> bytes:
    if not _BASE64URL_SEGMENT.fullmatch(segment):
        raise TokenError("Invalid access token")
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except binascii.Error as exc:
        raise TokenError("Invalid access token") from exc
