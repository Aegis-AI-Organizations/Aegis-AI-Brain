import enum
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

import asyncio
import grpc
import jwt

import aegis.v2.auth_pb2 as auth_pb2
import aegis.v2.auth_pb2_grpc as auth_pb2_grpc
from config.config import JWT_SECRET
from config.db import get_session_factory
from models.refresh_token import RefreshToken
from models.user import User
from utils.auth_utils import verify_password

logger = logging.getLogger(__name__)


class AuthErrorCode(enum.Enum):
    """Structured error codes for Auth synchronization methods."""

    SUCCESS = 0
    INVALID_CREDENTIALS = 1
    USER_INACTIVE = 2
    DB_ERROR = 3
    INVALID_TOKEN = 4


class AuthService(auth_pb2_grpc.AuthServiceServicer):
    """AuthService handles user login, token refresh, and logout."""

    def __init__(self):
        self._session_factory = None

    @property
    def session_factory(self):
        """Lazy-loaded session factory to avoid startup failure."""
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

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

    def _hash_token(self, token: str) -> str:
        """Helper to hash refresh tokens consistently."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _login_db_sync(self, request: auth_pb2.LoginRequest):
        """Synchronous part of Login logic."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == request.email).first()
            if not user or not verify_password(request.password, user.password_hash):
                return None, AuthErrorCode.INVALID_CREDENTIALS

            if not user.is_active:
                return None, AuthErrorCode.USER_INACTIVE

            # Generate tokens
            access_token = self._generate_access_token(user)
            raw_refresh_token = str(uuid.uuid4())
            token_hash = self._hash_token(raw_refresh_token)

            # Store hashed refresh token
            db_refresh_token = RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            try:
                db.add(db_refresh_token)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(f"Database error during login for {user.email}")
                return None, AuthErrorCode.DB_ERROR

            return (access_token, raw_refresh_token), AuthErrorCode.SUCCESS

    async def Login(
        self, request: auth_pb2.LoginRequest, context
    ) -> auth_pb2.LoginResponse:
        """Authenticates user and returns Access + Refresh tokens."""
        try:
            result, code = await asyncio.to_thread(self._login_db_sync, request)
        except Exception:
            logger.exception("Unexpected error in Login RPC")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal service error")
            return auth_pb2.LoginResponse()

        if code != AuthErrorCode.SUCCESS:
            if code == AuthErrorCode.INVALID_CREDENTIALS:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid email or password")
            elif code == AuthErrorCode.USER_INACTIVE:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("User account is inactive")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Internal authentication error")
            return auth_pb2.LoginResponse()

        access_token, refresh_token = result
        return auth_pb2.LoginResponse(
            access_token=access_token, refresh_token=refresh_token
        )

    def _refresh_db_sync(self, refresh_token: str):
        """Synchronous part of Refresh logic."""
        with self.session_factory() as db:
            lookup_hash = self._hash_token(refresh_token)
            token_entry = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == lookup_hash)
                .first()
            )

            if not token_entry or token_entry.revoked or token_entry.is_expired:
                return None, AuthErrorCode.INVALID_TOKEN

            return self._generate_access_token(token_entry.user), AuthErrorCode.SUCCESS

    async def Refresh(
        self, request: auth_pb2.RefreshRequest, context
    ) -> auth_pb2.RefreshResponse:
        """Validates refresh token and returns a new Access token."""
        try:
            access_token, code = await asyncio.to_thread(
                self._refresh_db_sync, request.refresh_token
            )
        except Exception:
            logger.exception("Unexpected error in Refresh RPC")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal service error")
            return auth_pb2.RefreshResponse()

        if code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid or expired refresh token")
            return auth_pb2.RefreshResponse()

        return auth_pb2.RefreshResponse(access_token=access_token)

    def _logout_db_sync(self, refresh_token: str) -> AuthErrorCode:
        """Synchronous part of Logout logic."""
        with self.session_factory() as db:
            lookup_hash = self._hash_token(refresh_token)
            token_entry = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == lookup_hash)
                .first()
            )

            if not token_entry:
                return AuthErrorCode.SUCCESS  # Idempotent

            try:
                token_entry.revoked = True
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Database error during logout")
                return AuthErrorCode.DB_ERROR

            return AuthErrorCode.SUCCESS

    async def Logout(
        self, request: auth_pb2.LogoutRequest, context
    ) -> auth_pb2.LogoutResponse:
        """Invalidates a refresh token by marking it as revoked."""
        try:
            code = await asyncio.to_thread(self._logout_db_sync, request.refresh_token)
        except Exception:
            logger.exception("Unexpected error in Logout RPC")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal service error")
            return auth_pb2.LogoutResponse(success=False)

        if code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to persist logout")
            return auth_pb2.LogoutResponse(success=False)

        return auth_pb2.LogoutResponse(success=True)
