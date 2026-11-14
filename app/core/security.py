def validate_jwt_secret(secret: str) -> None:
    if len(secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
