import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt

import aegis.v2.auth_pb2 as auth_pb2
import aegis.v2.auth_pb2_grpc as auth_pb2_grpc
from config.config import JWT_SECRET
from config.db import get_session_factory
from models.refresh_token import RefreshToken
from models.user import User
from utils.auth_utils import verify_password

logger = logging.getLogger(__name__)


class AuthService(auth_pb2_grpc.AuthServiceServicer):
    """AuthService handles user login, token refresh, and logout."""

    def __init__(self):
        self.session_factory = get_session_factory()

    def _generate_access_token(self, user: User) -> str:
        """Generates a JWT Access Token valid for 15 minutes."""
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    async def Login(
        self, request: auth_pb2.LoginRequest, context
    ) -> auth_pb2.LoginResponse:
        """Authenticates user and returns Access + Refresh tokens."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == request.email).first()
            if not user or not verify_password(request.password, user.password_hash):
                context.set_code(auth_pb2_grpc.grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid email or password")
                return auth_pb2.LoginResponse()

            if not user.is_active:
                context.set_code(auth_pb2_grpc.grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("User account is inactive")
                return auth_pb2.LoginResponse()

            # Generate tokens
            access_token = self._generate_access_token(user)
            raw_refresh_token = str(uuid.uuid4())
            import hashlib

            refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

            # Store hashed refresh token
            db_refresh_token = RefreshToken(
                user_id=user.id,
                token_hash=refresh_token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            db.add(db_refresh_token)
            db.commit()

            return auth_pb2.LoginResponse(
                access_token=access_token, refresh_token=raw_refresh_token
            )

    async def Refresh(
        self, request: auth_pb2.RefreshRequest, context
    ) -> auth_pb2.RefreshResponse:
        """Validates refresh token and returns a new Access token."""
        with self.session_factory() as db:
            # Note: We must fetch all tokens for evaluation since we hash them.
            # In a high-scale environment, we'd use a different lookup, but for now
            # we can use the hash as a unique key if we know how it was hashed.
            # But bcrypt hashes are salted, so we can't search by hash.
            # We'll use a simplified implementation for this specific requirement:
            # "hash is stored in the table refresh_tokens".

            # Since bcrypt is salted, we cannot querying by hash.
            # In reality, the Gateway should provide a session ID or we should use
            # a faster (unsalted or known salt) hash for indexing.
            # To respect the "store hash" requirement, I'll use a lookup by user and iterate.
            # Better approach: store a token ID in the JWT or cookie.
            # For this task, I'll perform a lookup that works with the existing schema.

            # Implementation decision: To support lookup, we'll need to store the hash
            # in a way that is searchable or use a different ID.
            # However, I will strictly follow the "hash and search" instruction by
            # using a non-random salt for the lookup-token or similar.
            # WAIT, the instruction said: "recevoir le token en clair... le hacher et le chercher".
            # This implies a deterministic hash for lookup. I'll use SHA256 for the lookup hash
            # to fulfill the "chercher par hash" requirement.

            import hashlib

            lookup_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()

            # I'll update the Login logic to store this searchable hash.
            # But I should check the RefreshToken model first.

            token_entry = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == lookup_hash)
                .first()
            )
            if not token_entry or token_entry.revoked or token_entry.is_expired:
                context.set_code(auth_pb2_grpc.grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid or expired refresh token")
                return auth_pb2.RefreshResponse()

            access_token = self._generate_access_token(token_entry.user)
            return auth_pb2.RefreshResponse(access_token=access_token)

    async def Logout(
        self, request: auth_pb2.LogoutRequest, context
    ) -> auth_pb2.LogoutResponse:
        """Invalidates a refresh token by marking it as revoked."""
        with self.session_factory() as db:
            import hashlib

            lookup_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()

            token_entry = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == lookup_hash)
                .first()
            )
            if token_entry:
                token_entry.revoked = True
                db.commit()

            return auth_pb2.LogoutResponse(success=True)
