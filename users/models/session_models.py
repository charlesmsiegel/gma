"""
Session management models for Issue #143: User Session Management and Security.

This module provides models for tracking user sessions, device information,
and security events related to session management.
"""

import hashlib
from datetime import timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import models
from django.utils import timezone


class SessionSecurityEvent:
    """Constants for session security event types."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    IP_ADDRESS_CHANGED = "ip_address_changed"
    USER_AGENT_CHANGED = "user_agent_changed"
    SESSION_EXTENDED = "session_extended"
    SESSION_TERMINATED = "session_terminated"
    CONCURRENT_SESSION_LIMIT = "concurrent_session_limit"
    PASSWORD_CHANGED = "password_changed"  # nosec B105
    ACCOUNT_LOCKED = "account_locked"

    @classmethod
    def get_security_events(cls) -> set[str]:
        """Return events that are considered security-related."""
        return {
            cls.SESSION_HIJACK_ATTEMPT,
            cls.SUSPICIOUS_ACTIVITY,
            cls.IP_ADDRESS_CHANGED,
            cls.USER_AGENT_CHANGED,
            cls.CONCURRENT_SESSION_LIMIT,
            cls.ACCOUNT_LOCKED,
        }

    @classmethod
    def get_all_choices(cls) -> list[tuple[str, str]]:
        """Return all event types as Django choices."""
        return [
            (cls.LOGIN_SUCCESS, "Login Success"),
            (cls.LOGIN_FAILED, "Login Failed"),
            (cls.LOGOUT, "Logout"),
            (cls.SESSION_HIJACK_ATTEMPT, "Session Hijack Attempt"),
            (cls.SUSPICIOUS_ACTIVITY, "Suspicious Activity"),
            (cls.IP_ADDRESS_CHANGED, "IP Address Changed"),
            (cls.USER_AGENT_CHANGED, "User Agent Changed"),
            (cls.SESSION_EXTENDED, "Session Extended"),
            (cls.SESSION_TERMINATED, "Session Terminated"),
            (cls.CONCURRENT_SESSION_LIMIT, "Concurrent Session Limit"),
            (cls.PASSWORD_CHANGED, "Password Changed"),
            (cls.ACCOUNT_LOCKED, "Account Locked"),
        ]


class UserSessionQuerySet(models.QuerySet):
    """Custom queryset for UserSession model with chainable methods."""

    def active(self):
        """Return only active sessions."""
        return self.filter(is_active=True)

    def for_user(self, user):
        """Return sessions for a specific user."""
        return self.filter(user=user)

    def expired(self):
        """Return expired sessions based on Django session expiry."""
        return self.filter(session__expire_date__lt=timezone.now())


class UserSessionManager(models.Manager):
    """Custom manager for UserSession model."""

    def get_queryset(self):
        """Return custom queryset with chainable methods."""
        return UserSessionQuerySet(self.model, using=self._db)

    def active(self):
        """Return only active sessions."""
        return self.get_queryset().active()

    def for_user(self, user):
        """Return sessions for a specific user."""
        return self.get_queryset().for_user(user)

    def expired(self):
        """Return expired sessions based on Django session expiry."""
        return self.get_queryset().expired()

    def cleanup_expired(self):
        """Clean up expired sessions and delete associated UserSessions."""
        expired_sessions = self.expired()
        count = expired_sessions.count()

        # Delete expired UserSessions
        # This will trigger SET_NULL on related SessionSecurityLog records
        expired_sessions.delete()

        return count


class UserSession(models.Model):
    """
    Model to track user sessions with device and security information.

    Extends Django's session system with additional tracking capabilities
    for security monitoring and device management.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text="The user this session belongs to",
    )

    session = models.OneToOneField(
        Session,
        on_delete=models.CASCADE,
        unique=True,
        help_text="Associated Django session",
    )

    # Device and browser information
    ip_address = models.GenericIPAddressField(
        help_text="IP address when session was created"
    )
    user_agent = models.TextField(help_text="User agent string from browser")
    device_type = models.CharField(
        max_length=20, blank=True, help_text="Device type (desktop, mobile, tablet)"
    )
    browser = models.CharField(
        max_length=50, blank=True, help_text="Browser name and version"
    )
    operating_system = models.CharField(
        max_length=50, blank=True, help_text="Operating system information"
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="Approximate location based on IP"
    )

    # Session management
    is_active = models.BooleanField(
        default=True, help_text="Whether the session is currently active"
    )
    remember_me = models.BooleanField(
        default=False, help_text="Whether this is a 'remember me' session"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the session was created"
    )
    last_activity = models.DateTimeField(
        auto_now=True, help_text="Last activity timestamp"
    )
    ended_at = models.DateTimeField(
        null=True, blank=True, help_text="When the session was ended"
    )

    objects = UserSessionManager()

    class Meta:
        db_table = "users_user_session"
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["last_activity"]),
        ]

    def __str__(self) -> str:
        """Return string representation of the user session."""
        device_info = (
            f"{self.browser}/{self.device_type}"
            if self.browser and self.device_type
            else "Unknown"
        )
        return f"{self.user.username} - {device_info} from {self.ip_address}"

    @property
    def device_fingerprint(self) -> str:
        """
        Generate a device fingerprint based on user agent and other factors.

        This creates a unique identifier for the device/browser combination
        that can be used for security analysis.
        """
        fingerprint_data = (
            f"{self.user_agent}"
            f"{self.device_type}"
            f"{self.browser}"
            f"{self.operating_system}"
        )

        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def is_suspicious_activity(self, ip_address: str, user_agent: str) -> bool:
        """
        Check if the given IP address and user agent indicate suspicious activity.

        Args:
            ip_address: New IP address to check
            user_agent: New user agent to check

        Returns:
            True if activity appears suspicious, False otherwise
        """
        # Check for IP address changes
        if self.ip_address != ip_address:
            return True

        # Check for significant user agent changes
        if self.user_agent != user_agent:
            return True

        return False

    def update_activity(
        self, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> None:
        """
        Update last activity timestamp and optionally check for suspicious activity.

        Args:
            ip_address: Current IP address (optional)
            user_agent: Current user agent (optional)
        """
        # If IP or user agent provided, check for suspicious activity
        if ip_address or user_agent:
            if self.is_suspicious_activity(
                ip_address or self.ip_address, user_agent or self.user_agent
            ):
                # Log suspicious activity
                SessionSecurityLog.objects.create(
                    user=self.user,
                    user_session=self,
                    event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
                    ip_address=ip_address or self.ip_address,
                    user_agent=user_agent or self.user_agent,
                    details={
                        "original_ip": self.ip_address,
                        "original_user_agent": self.user_agent,
                        "new_ip": ip_address,
                        "new_user_agent": user_agent,
                    },
                )

        self.last_activity = timezone.now()
        self.save(update_fields=["last_activity"])

    def deactivate(self) -> None:
        """Deactivate the session."""
        self.is_active = False
        self.ended_at = timezone.now()
        self.save(update_fields=["is_active", "ended_at"])

    def extend_expiry(self, hours: int = 24) -> None:
        """
        Extend session expiry time.

        Args:
            hours: Number of hours to extend the session
        """
        # Extend from the current expiry date, not current time
        self.session.expire_date = self.session.expire_date + timedelta(hours=hours)
        self.session.save(update_fields=["expire_date"])

        # Log the extension
        SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self,
            event_type=SessionSecurityEvent.SESSION_EXTENDED,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            details={"extension_hours": hours},
        )

    def extend_for_remember_me(self) -> None:
        """Extend session for remember me functionality (30 days)."""
        self.extend_expiry(hours=24 * 30)  # 30 days


class SessionSecurityLogQuerySet(models.QuerySet):
    """Custom queryset for SessionSecurityLog model with chainable methods."""

    def for_user(self, user):
        """Return security logs for a specific user."""
        return self.filter(user=user)

    def security_events(self):
        """Return only security-related events."""
        security_event_types = SessionSecurityEvent.get_security_events()
        return self.filter(event_type__in=security_event_types)

    def recent(self, hours: int = 24):
        """Return recent log entries within the specified hours."""
        since = timezone.now() - timedelta(hours=hours)
        return self.filter(timestamp__gte=since)


class SessionSecurityLogManager(models.Manager):
    """Custom manager for SessionSecurityLog model."""

    def get_queryset(self):
        """Return custom queryset with chainable methods."""
        return SessionSecurityLogQuerySet(self.model, using=self._db)

    def for_user(self, user):
        """Return security logs for a specific user."""
        return self.get_queryset().for_user(user)

    def security_events(self):
        """Return only security-related events."""
        return self.get_queryset().security_events()

    def recent(self, hours: int = 24):
        """Return recent log entries within the specified hours."""
        return self.get_queryset().recent(hours)


class SessionSecurityLog(models.Model):
    """
    Model to log security events related to user sessions.

    This model tracks all security-relevant events for audit and
    monitoring purposes.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_logs",
        help_text="User associated with this security event",
    )

    user_session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_logs",
        help_text="Session associated with this event (if applicable)",
    )

    event_type = models.CharField(
        max_length=50,
        choices=SessionSecurityEvent.get_all_choices(),
        help_text="Type of security event",
    )

    ip_address = models.GenericIPAddressField(
        help_text="IP address where event occurred"
    )

    user_agent = models.TextField(
        blank=True, help_text="User agent string when event occurred"
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the security event",
    )

    timestamp = models.DateTimeField(
        auto_now_add=True, help_text="When the security event occurred"
    )

    objects = SessionSecurityLogManager()

    class Meta:
        db_table = "users_session_security_log"
        verbose_name = "Session Security Log"
        verbose_name_plural = "Session Security Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "event_type"]),
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self) -> str:
        """Return string representation of the security log entry."""
        return (
            f"{self.user.username} - {self.event_type.upper()} from {self.ip_address}"
        )

    @classmethod
    def log_event(
        cls,
        user,
        event_type: str,
        ip_address: str,
        user_agent: str = "",
        user_session: Optional["UserSession"] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "SessionSecurityLog":
        """
        Convenience method to create a security log entry.

        Args:
            user: User instance
            event_type: Type of security event
            ip_address: IP address where event occurred
            user_agent: User agent string
            user_session: Associated UserSession (optional)
            details: Additional event details

        Returns:
            Created SessionSecurityLog instance
        """
        return cls.objects.create(
            user=user,
            user_session=user_session,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
