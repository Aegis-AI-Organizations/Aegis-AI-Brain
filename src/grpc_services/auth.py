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
from sqlalchemy.orm import joinedload
from models.onboarding_invitation import OnboardingInvitation
from models.refresh_token import RefreshToken
from models.user import User, UserActivationStatus
from utils.auth_utils import verify_password, hash_password
from utils.token_utils import hash_token
from grpc_services.utils import with_identity

logger = logging.getLogger(__name__)


class AuthErrorCode(enum.Enum):
    """Structured error codes for Auth synchronization methods."""

    SUCCESS = 0
    INVALID_CREDENTIALS = 1
    USER_INACTIVE = 2
    DB_ERROR = 3
    INVALID_TOKEN = 4
    USER_NOT_FOUND = 5


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
            "company_id": str(user.company_id) if user.company_id else None,
            "email": user.email,
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    def _hash_token(self, token: str) -> str:
        """Helper to hash refresh tokens consistently."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _create_session_tokens(self, db, user: User):
        access_token = self._generate_access_token(user)
        raw_refresh_token = str(uuid.uuid4())
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=self._hash_token(raw_refresh_token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        return access_token, raw_refresh_token

    def _login_db_sync(self, request: auth_pb2.LoginRequest):
        """Synchronous part of Login logic."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == request.email).first()
            if not user or not verify_password(request.password, user.password_hash):
                return None, AuthErrorCode.INVALID_CREDENTIALS

            if not user.is_active:
                return None, AuthErrorCode.USER_INACTIVE

            try:
                access_token, raw_refresh_token = self._create_session_tokens(db, user)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(f"Database error during login for user ID: {user.id}")
                return None, AuthErrorCode.DB_ERROR

            return (access_token, raw_refresh_token), AuthErrorCode.SUCCESS

    def _setup_password_db_sync(self, invitation_token: str, new_password: str):
        with self.session_factory() as db:
            invitation = (
                db.query(OnboardingInvitation)
                .options(joinedload(OnboardingInvitation.user))
                .filter(OnboardingInvitation.token_hash == hash_token(invitation_token))
                .first()
            )

            if not invitation or invitation.is_used or invitation.is_expired:
                return None, AuthErrorCode.INVALID_TOKEN

            user = invitation.user
            if not user:
                return None, AuthErrorCode.USER_NOT_FOUND

            if (
                user.activation_status != UserActivationStatus.pending_activation
                or user.is_active
            ):
                return None, AuthErrorCode.INVALID_TOKEN

            try:
                user.password_hash = hash_password(new_password)
                user.is_active = True
                user.activation_status = UserActivationStatus.active
                invitation.used_at = datetime.now(timezone.utc)
                access_token, refresh_token = self._create_session_tokens(db, user)
                db.commit()
                return (access_token, refresh_token), AuthErrorCode.SUCCESS
            except Exception:
                db.rollback()
                logger.exception(
                    "Database error during setup-password for user ID: %s", user.id
                )
                return None, AuthErrorCode.DB_ERROR

    async def SetupPassword(
        self, request: auth_pb2.SetupPasswordRequest, context
    ) -> auth_pb2.SetupPasswordResponse:
        """Activates an invited account and starts a user session."""
        try:
            result, code = await asyncio.to_thread(
                self._setup_password_db_sync,
                request.invitation_token,
                request.new_password,
            )
        except Exception:
            logger.exception("Unexpected error in SetupPassword RPC")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal service error")
            return auth_pb2.SetupPasswordResponse()

        if code != AuthErrorCode.SUCCESS:
            if code == AuthErrorCode.INVALID_TOKEN:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid or expired invitation token")
            elif code == AuthErrorCode.USER_NOT_FOUND:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Invited user not found")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Internal activation error")
            return auth_pb2.SetupPasswordResponse()

        access_token, refresh_token = result
        return auth_pb2.SetupPasswordResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

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

    def _get_me_db_sync(self, user_id: str):
        """Synchronous part of GetMe logic."""
        with self.session_factory() as db:
            user = (
                db.query(User)
                .options(joinedload(User.company))
                .filter(User.id == user_id)
                .first()
            )
            if not user or not user.is_active:
                return None, AuthErrorCode.USER_INACTIVE

            # Extract data while session is open to avoid DetachedInstanceError
            user_data = {
                "id": str(user.id),
                "name": user.name or "",
                "avatar_url": user.avatar_url or "",
                "email": user.email,
                "role": user.role if isinstance(user.role, str) else user.role.value,
                "company_id": str(user.company_id) if user.company_id else "",
                "company_name": user.company.name if user.company else "",
            }

            return user_data, AuthErrorCode.SUCCESS

    @with_identity(verified_only=True)
    async def GetMe(self, request, context, identity) -> auth_pb2.GetMeResponse:
        """Retrieves the authenticated user's profile based on verified JWT identity."""
        user_id = identity["user_id"]

        try:
            user, code = await asyncio.to_thread(self._get_me_db_sync, user_id)
        except Exception:
            logger.exception("Unexpected error in GetMe RPC")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal service error")
            return auth_pb2.GetMeResponse()

        if code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found or inactive")
            return auth_pb2.GetMeResponse()

        return auth_pb2.GetMeResponse(
            id=user["id"],  # Fix typo: user is now a dict
            name=user["name"],
            email=user["email"],
            role=user["role"],
            company_id=user["company_id"],
            company_name=user["company_name"],
            avatar_url=user["avatar_url"],
        )

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

    def _update_profile_db_sync(
        self, user_id: str, name: str, avatar_url: str = None
    ) -> AuthErrorCode:
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return AuthErrorCode.USER_NOT_FOUND
            try:
                user.name = name
                if avatar_url is not None:
                    user.avatar_url = avatar_url
                db.commit()
                return AuthErrorCode.SUCCESS
            except Exception:
                db.rollback()
                return AuthErrorCode.DB_ERROR

    @with_identity(verified_only=True)
    async def UpdateProfile(
        self, request: auth_pb2.UpdateProfileRequest, context, identity
    ) -> auth_pb2.UpdateProfileResponse:
        user_id = identity["user_id"]
        code = await asyncio.to_thread(
            self._update_profile_db_sync, user_id, request.name, request.avatar_url
        )
        if code == AuthErrorCode.USER_NOT_FOUND:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return auth_pb2.UpdateProfileResponse(success=False)
        elif code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.UpdateProfileResponse(success=False)

        return auth_pb2.UpdateProfileResponse(success=True)

    def _update_email_db_sync(self, user_id: str, new_email: str) -> AuthErrorCode:
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return AuthErrorCode.USER_NOT_FOUND

            # Check if email is already in use by someone ELSE
            existing = db.query(User).filter(User.email == new_email).first()
            if existing and existing.id != user.id:
                return AuthErrorCode.INVALID_CREDENTIALS  # Conflict

            try:
                user.email = new_email
                db.commit()
                return AuthErrorCode.SUCCESS
            except Exception:
                db.rollback()
                return AuthErrorCode.DB_ERROR

    @with_identity(verified_only=True)
    async def UpdateEmail(
        self, request: auth_pb2.UpdateEmailRequest, context, identity
    ) -> auth_pb2.UpdateEmailResponse:
        user_id = identity["user_id"]
        code = await asyncio.to_thread(
            self._update_email_db_sync, user_id, request.new_email
        )
        if code == AuthErrorCode.INVALID_CREDENTIALS:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Email already in use")
            return auth_pb2.UpdateEmailResponse(success=False)
        elif code == AuthErrorCode.USER_NOT_FOUND:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return auth_pb2.UpdateEmailResponse(success=False)
        elif code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.UpdateEmailResponse(success=False)

        return auth_pb2.UpdateEmailResponse(success=True)

    def _update_password_db_sync(
        self, user_id: str, old_pwd: str, new_pwd: str
    ) -> AuthErrorCode:
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return AuthErrorCode.USER_NOT_FOUND

            if not verify_password(old_pwd, user.password_hash):
                return AuthErrorCode.INVALID_CREDENTIALS

            try:
                user.password_hash = hash_password(new_pwd)
                db.commit()
                return AuthErrorCode.SUCCESS
            except Exception:
                db.rollback()
                return AuthErrorCode.DB_ERROR

    @with_identity(verified_only=True)
    async def UpdatePassword(
        self, request: auth_pb2.UpdatePasswordRequest, context, identity
    ) -> auth_pb2.UpdatePasswordResponse:
        user_id = identity["user_id"]
        code = await asyncio.to_thread(
            self._update_password_db_sync,
            user_id,
            request.old_password,
            request.new_password,
        )
        if code == AuthErrorCode.INVALID_CREDENTIALS:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid old password")
            return auth_pb2.UpdatePasswordResponse(success=False)
        elif code == AuthErrorCode.USER_NOT_FOUND:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return auth_pb2.UpdatePasswordResponse(success=False)
        elif code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.UpdatePasswordResponse(success=False)

        return auth_pb2.UpdatePasswordResponse(success=True)

    def _remove_avatar_db_sync(self, user_id: str) -> AuthErrorCode:
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return AuthErrorCode.USER_NOT_FOUND
            try:
                user.avatar_url = None
                db.commit()
                return AuthErrorCode.SUCCESS
            except Exception:
                db.rollback()
                return AuthErrorCode.DB_ERROR

    @with_identity(verified_only=True)
    async def RemoveAvatar(
        self, request: auth_pb2.RemoveAvatarRequest, context, identity
    ) -> auth_pb2.RemoveAvatarResponse:
        user_id = identity["user_id"]
        code = await asyncio.to_thread(self._remove_avatar_db_sync, user_id)
        if code != AuthErrorCode.SUCCESS:
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.RemoveAvatarResponse(success=False)
        return auth_pb2.RemoveAvatarResponse(success=True)
