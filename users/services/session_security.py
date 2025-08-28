"""
Session Security Service for Issue #143: User Session Management and Security.

This service provides comprehensive session security monitoring including:
- Suspicious activity detection
- Risk assessment and scoring
- Security alert generation
- Session management and cleanup
- Geographic and behavioral analysis
"""

import hashlib
import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from ..models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class SessionSecurityService:
    """Service for managing session security monitoring and alerts."""

    def __init__(self):
        """Initialize the session security service."""
        self.max_concurrent_sessions = getattr(settings, "MAX_CONCURRENT_SESSIONS", 5)
        self.security_alert_cooldown = getattr(
            settings, "SECURITY_ALERT_COOLDOWN_MINUTES", 60
        )
        self.high_risk_threshold = getattr(settings, "HIGH_RISK_THRESHOLD", 8.0)
        self.auto_terminate_threshold = getattr(
            settings, "AUTO_TERMINATE_THRESHOLD", 9.0
        )

    def create_user_session(
        self, user: User, session: Session, ip_address: str, user_agent: str, **kwargs
    ) -> UserSession:
        """
        Create a new UserSession with device information.

        Args:
            user: User instance
            session: Django Session instance
            ip_address: Client IP address
            user_agent: Browser user agent string
            **kwargs: Additional session data

        Returns:
            Created UserSession instance
        """
        # Parse user agent for device information
        device_info = self._parse_user_agent(user_agent)

        # Get geolocation information
        location = self._get_location_from_ip(ip_address)

        user_session = UserSession.objects.create(
            user=user,
            session=session,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info.get("device_type", ""),
            browser=device_info.get("browser", ""),
            operating_system=device_info.get("os", ""),
            location=location,
            **kwargs,
        )

        # Log successful login
        SessionSecurityLog.log_event(
            user=user,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            user_session=user_session,
            details={"device_info": device_info, "location": location},
        )

        # Check for concurrent session anomalies
        if self.detect_concurrent_session_anomaly(user):
            self._handle_concurrent_session_alert(user, user_session)

        return user_session

    def handle_request_security_check(
        self, user_session: UserSession, new_ip: str, new_user_agent: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle security checking for ongoing requests.

        Args:
            user_session: Current UserSession
            new_ip: Current request IP address
            new_user_agent: Current request user agent

        Returns:
            Security assessment results or None if no issues
        """
        security_issues = []

        # Check for IP address changes
        if user_session.ip_address != new_ip:
            self._log_ip_address_change(user_session, new_ip, new_user_agent)
            security_issues.append("ip_changed")

        # Check for user agent changes
        if user_session.user_agent != new_user_agent:
            self._log_user_agent_change(user_session, new_ip, new_user_agent)
            security_issues.append("user_agent_changed")

        # If we have security issues, assess risk
        if security_issues:
            risk_score = self.calculate_risk_score(
                event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
                ip_address_changed="ip_changed" in security_issues,
                user_agent_changed="user_agent_changed" in security_issues,
                session=user_session,
            )

            # Handle based on risk level
            return self.handle_suspicious_activity(
                user_session, new_ip, new_user_agent, risk_score=risk_score
            )

        # Update session activity if no issues
        user_session.update_activity(new_ip, new_user_agent)
        return None

    def detect_suspicious_activity(
        self, user_session: UserSession, new_ip: str, new_user_agent: str
    ) -> bool:
        """
        Detect if current activity is suspicious.

        Args:
            user_session: Current UserSession
            new_ip: New IP address
            new_user_agent: New user agent

        Returns:
            True if activity is suspicious, False otherwise
        """
        return user_session.is_suspicious_activity(new_ip, new_user_agent)

    def detect_concurrent_session_anomaly(self, user: User) -> bool:
        """
        Detect anomalous concurrent session patterns.

        Args:
            user: User to check

        Returns:
            True if anomaly detected, False otherwise
        """
        active_sessions = UserSession.objects.active().for_user(user)

        # Check total number of sessions
        if active_sessions.count() > self.max_concurrent_sessions:
            return True

        # Check for sessions from widely different locations
        if active_sessions.count() >= 2:
            locations = set(
                session.location for session in active_sessions if session.location
            )

            # If we have sessions from 3+ different locations, flag as suspicious
            if len(locations) >= 3:
                return True

            # Check for impossible travel (sessions from very different locations)
            ip_addresses = list(active_sessions.values_list("ip_address", flat=True))
            if self._detect_impossible_travel(ip_addresses):
                return True

        return False

    def detect_geographic_anomaly(self, user_session: UserSession, new_ip: str) -> bool:
        """
        Detect geographic anomalies in session access.

        Args:
            user_session: Current session
            new_ip: New IP address

        Returns:
            True if geographic anomaly detected
        """
        old_location = self.get_geolocation(user_session.ip_address)
        new_location = self.get_geolocation(new_ip)

        # If we can't determine locations, be cautious
        if not old_location or not new_location:
            return True

        # Check for different countries
        if old_location.get("country") != new_location.get("country"):
            return True

        # Check for significant distance (would need geolocation calculation)
        # For now, just check different regions
        if old_location.get("region") != new_location.get("region"):
            return True

        return False

    def detect_timing_anomaly(self, user: User) -> bool:
        """
        Detect timing anomalies in user access patterns.

        Args:
            user: User to analyze

        Returns:
            True if timing anomaly detected
        """
        # Get recent login patterns
        recent_logs = SessionSecurityLog.objects.filter(
            user=user,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            timestamp__gte=timezone.now() - timedelta(days=30),
        ).order_by("-timestamp")[:10]

        if recent_logs.count() < 3:
            # Not enough data for analysis
            return False

        # Analyze login times (simplified version)
        current_hour = timezone.now().hour

        # Check if current login is significantly different from usual pattern
        usual_hours = [log.timestamp.hour for log in recent_logs]

        # If current hour is more than 6 hours from typical login times, flag it
        min_usual = min(usual_hours)
        max_usual = max(usual_hours)

        if current_hour < min_usual - 6 or current_hour > max_usual + 6:
            return True

        return False

    def detect_device_fingerprint_mismatch(
        self, user_session: UserSession, new_fingerprint: str
    ) -> bool:
        """
        Detect device fingerprint mismatches.

        Args:
            user_session: Current session
            new_fingerprint: New device fingerprint

        Returns:
            True if fingerprint mismatch detected
        """
        return user_session.device_fingerprint != new_fingerprint

    def calculate_risk_score(
        self,
        event_type: str,
        ip_address_changed: bool = False,
        user_agent_changed: bool = False,
        session: Optional[UserSession] = None,
        **kwargs,
    ) -> float:
        """
        Calculate risk score for security event.

        Args:
            event_type: Type of security event
            ip_address_changed: Whether IP address changed
            user_agent_changed: Whether user agent changed
            session: Associated session (optional)
            **kwargs: Additional risk factors

        Returns:
            Risk score between 0.0 and 10.0
        """
        risk_score = 0.0

        # Base score by event type
        event_risk_scores = {
            SessionSecurityEvent.LOGIN_SUCCESS: 1.0,
            SessionSecurityEvent.LOGIN_FAILED: 3.0,
            SessionSecurityEvent.SUSPICIOUS_ACTIVITY: 6.0,
            SessionSecurityEvent.IP_ADDRESS_CHANGED: 5.0,
            SessionSecurityEvent.USER_AGENT_CHANGED: 4.0,
            SessionSecurityEvent.SESSION_HIJACK_ATTEMPT: 9.5,
            SessionSecurityEvent.CONCURRENT_SESSION_LIMIT: 7.0,
        }

        risk_score += event_risk_scores.get(event_type, 3.0)

        # Additional risk factors
        if ip_address_changed:
            risk_score += 2.0

        if user_agent_changed:
            risk_score += 1.5

        # Geographic risk (if session provided)
        if session:
            recent_ips = (
                SessionSecurityLog.objects.filter(
                    user=session.user,
                    timestamp__gte=timezone.now() - timedelta(hours=24),
                )
                .values_list("ip_address", flat=True)
                .distinct()
            )

            # More unique IPs in recent time = higher risk
            if len(set(recent_ips)) > 3:
                risk_score += 1.0

        # Cap at 10.0
        return min(risk_score, 10.0)

    def handle_suspicious_activity(
        self,
        user_session: UserSession,
        new_ip: str,
        new_user_agent: str,
        risk_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Handle detected suspicious activity.

        Args:
            user_session: Affected session
            new_ip: New IP address
            new_user_agent: New user agent
            risk_score: Calculated risk score (optional)

        Returns:
            Dictionary with handling results
        """
        if risk_score is None:
            risk_score = self.calculate_risk_score(
                event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
                ip_address_changed=(user_session.ip_address != new_ip),
                user_agent_changed=(user_session.user_agent != new_user_agent),
                session=user_session,
            )

        result = {"risk_score": risk_score, "actions_taken": []}

        # Log the suspicious activity
        SessionSecurityLog.log_event(
            user=user_session.user,
            event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            ip_address=new_ip,
            user_agent=new_user_agent,
            user_session=user_session,
            details={
                "risk_score": risk_score,
                "original_ip": user_session.ip_address,
                "original_user_agent": user_session.user_agent,
            },
        )

        # Handle based on risk level
        if risk_score >= self.auto_terminate_threshold:
            # Terminate session immediately
            user_session.deactivate()

            # Log session hijack attempt
            SessionSecurityLog.log_event(
                user=user_session.user,
                event_type=SessionSecurityEvent.SESSION_HIJACK_ATTEMPT,
                ip_address=new_ip,
                user_agent=new_user_agent,
                user_session=user_session,
                details={"risk_score": risk_score, "auto_terminated": True},
            )

            result["actions_taken"].append("session_terminated")

            # Send immediate security alert
            self.send_security_alert(
                user_session.user,
                event_type=SessionSecurityEvent.SESSION_HIJACK_ATTEMPT,
                details={
                    "ip_address": new_ip,
                    "user_agent": new_user_agent,
                    "risk_score": risk_score,
                },
            )
            result["actions_taken"].append("security_alert_sent")

        elif risk_score >= self.high_risk_threshold:
            # Send security alert but don't terminate
            self.send_security_alert(
                user_session.user,
                event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
                details={
                    "ip_address": new_ip,
                    "user_agent": new_user_agent,
                    "risk_score": risk_score,
                },
            )
            result["actions_taken"].append("security_alert_sent")

        return result

    def send_security_alert(
        self, user: User, event_type: str, details: Dict[str, Any]
    ) -> bool:
        """
        Send security alert to user.

        Args:
            user: User to alert
            event_type: Type of security event
            details: Event details

        Returns:
            True if alert sent successfully
        """
        # Check rate limiting
        recent_alerts = SessionSecurityLog.objects.filter(
            user=user,
            event_type__in=SessionSecurityEvent.get_security_events(),
            timestamp__gte=timezone.now()
            - timedelta(minutes=self.security_alert_cooldown),
        ).count()

        if recent_alerts >= 3:  # Max 3 alerts per hour
            return False

        try:
            subject = (
                f"Security Alert for {getattr(settings, 'SITE_NAME', 'Your Account')}"
            )

            context = {
                "user": user,
                "event_type": event_type,
                "details": details,
                "site_name": getattr(settings, "SITE_NAME", "Your Account"),
            }

            message = render_to_string("users/emails/security_alert.html", context)

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
                ),
                recipient_list=[user.email],
                html_message=message,
                fail_silently=False,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send security alert to {user.email}: {e}")
            return False

    def get_security_dashboard_data(self, user: User) -> Dict[str, Any]:
        """
        Get security dashboard data for user.

        Args:
            user: User to get data for

        Returns:
            Dictionary with security dashboard data
        """
        now = timezone.now()

        # Get recent security events
        recent_events = SessionSecurityLog.objects.filter(
            user=user, timestamp__gte=now - timedelta(days=30)
        )

        security_events = recent_events.filter(
            event_type__in=SessionSecurityEvent.get_security_events()
        )

        # Get active sessions
        active_sessions = UserSession.objects.active().for_user(user)

        # Calculate risk level
        recent_risk_scores = [
            log.details.get("risk_score", 0)
            for log in security_events[:10]
            if "risk_score" in log.details
        ]

        avg_risk_score = (
            sum(recent_risk_scores) / len(recent_risk_scores)
            if recent_risk_scores
            else 0
        )

        risk_level = "low"
        if avg_risk_score >= 7.0:
            risk_level = "high"
        elif avg_risk_score >= 4.0:
            risk_level = "medium"

        return {
            "total_events": recent_events.count(),
            "security_events": security_events.count(),
            "recent_logins": recent_events.filter(
                event_type=SessionSecurityEvent.LOGIN_SUCCESS
            ).count(),
            "active_sessions": active_sessions.count(),
            "risk_level": risk_level,
            "average_risk_score": avg_risk_score,
            "recent_security_events": [
                {
                    "event_type": log.event_type,
                    "timestamp": log.timestamp,
                    "ip_address": log.ip_address,
                    "details": log.details,
                }
                for log in security_events[:5]
            ],
        }

    def correlate_security_events(
        self, user: User, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Correlate related security events.

        Args:
            user: User to analyze
            hours: Time window for correlation

        Returns:
            List of correlated event groups
        """
        # Get recent events
        since = timezone.now() - timedelta(hours=hours)
        events = SessionSecurityLog.objects.filter(
            user=user, timestamp__gte=since
        ).order_by("timestamp")

        correlated_events = []

        # Group events by IP address and time proximity
        event_groups = {}

        for event in events:
            # Create group key based on IP and time window (30-minute windows)
            time_window = event.timestamp.replace(
                minute=(event.timestamp.minute // 30) * 30, second=0, microsecond=0
            )
            group_key = f"{event.ip_address}_{time_window}"

            if group_key not in event_groups:
                event_groups[group_key] = []

            event_groups[group_key].append(
                {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "ip_address": event.ip_address,
                    "details": event.details,
                }
            )

        # Calculate correlation scores
        for group_key, group_events in event_groups.items():
            if len(group_events) > 1:
                # Higher correlation score for more events in same time/location
                correlation_score = min(len(group_events) / 5.0, 1.0)

                # Boost score for security events
                security_event_count = sum(
                    1
                    for event in group_events
                    if event["event_type"] in SessionSecurityEvent.get_security_events()
                )

                if security_event_count > 0:
                    correlation_score += 0.3

                correlated_events.append(
                    {
                        "group_key": group_key,
                        "events": group_events,
                        "correlation_score": min(correlation_score, 1.0),
                        "event_count": len(group_events),
                        "security_event_count": security_event_count,
                    }
                )

        # Sort by correlation score descending
        correlated_events.sort(key=lambda x: x["correlation_score"], reverse=True)

        return correlated_events

    def calculate_device_fingerprint(self, **device_data) -> str:
        """
        Calculate device fingerprint from device data.

        Args:
            **device_data: Device characteristics

        Returns:
            SHA-256 hash of device fingerprint
        """
        fingerprint_data = (
            f"{device_data.get('user_agent', '')}"
            f"{device_data.get('device_type', '')}"
            f"{device_data.get('browser', '')}"
            f"{device_data.get('operating_system', '')}"
        )

        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def get_geolocation(self, ip_address: str) -> Optional[Dict[str, str]]:
        """
        Get geolocation information for IP address.

        Args:
            ip_address: IP address to look up

        Returns:
            Dictionary with location info or None
        """
        # In a real implementation, this would use a geolocation service
        # like MaxMind GeoIP, IP-API, or similar

        # For testing, return mock data
        if ip_address.startswith("192.168.") or ip_address.startswith("10."):
            return {"country": "US", "region": "CA", "city": "Local"}
        elif ip_address.startswith("203.0.113."):
            return {"country": "GB", "region": "London", "city": "London"}
        else:
            return {"country": "Unknown", "region": "Unknown", "city": "Unknown"}

    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """
        Parse user agent string for device information.

        Args:
            user_agent: User agent string

        Returns:
            Dictionary with parsed device info
        """
        # Simplified user agent parsing
        # In production, use a library like user-agents or ua-parser

        device_info = {"device_type": "desktop", "browser": "Unknown", "os": "Unknown"}

        user_agent_lower = user_agent.lower()

        # Detect device type
        if any(
            mobile in user_agent_lower for mobile in ["mobile", "android", "iphone"]
        ):
            device_info["device_type"] = "mobile"
        elif any(tablet in user_agent_lower for tablet in ["tablet", "ipad"]):
            device_info["device_type"] = "tablet"

        # Detect browser
        if "chrome" in user_agent_lower:
            device_info["browser"] = "Chrome"
        elif "firefox" in user_agent_lower:
            device_info["browser"] = "Firefox"
        elif "safari" in user_agent_lower:
            device_info["browser"] = "Safari"
        elif "edge" in user_agent_lower:
            device_info["browser"] = "Edge"

        # Detect OS
        if "windows" in user_agent_lower:
            device_info["os"] = "Windows"
        elif "mac os" in user_agent_lower:
            device_info["os"] = "macOS"
        elif "linux" in user_agent_lower:
            device_info["os"] = "Linux"
        elif "android" in user_agent_lower:
            device_info["os"] = "Android"
        elif "ios" in user_agent_lower:
            device_info["os"] = "iOS"

        return device_info

    def _get_location_from_ip(self, ip_address: str) -> str:
        """
        Get location string from IP address.

        Args:
            ip_address: IP address

        Returns:
            Location string
        """
        geo_info = self.get_geolocation(ip_address)
        if geo_info and geo_info["city"] != "Unknown":
            return f"{geo_info['city']}, {geo_info['region']}"
        return ""

    def _log_ip_address_change(
        self, user_session: UserSession, new_ip: str, new_user_agent: str
    ) -> None:
        """Log IP address change event."""
        SessionSecurityLog.log_event(
            user=user_session.user,
            event_type=SessionSecurityEvent.IP_ADDRESS_CHANGED,
            ip_address=new_ip,
            user_agent=new_user_agent,
            user_session=user_session,
            details={"old_ip": user_session.ip_address, "new_ip": new_ip},
        )

    def _log_user_agent_change(
        self, user_session: UserSession, new_ip: str, new_user_agent: str
    ) -> None:
        """Log user agent change event."""
        SessionSecurityLog.log_event(
            user=user_session.user,
            event_type=SessionSecurityEvent.USER_AGENT_CHANGED,
            ip_address=new_ip,
            user_agent=new_user_agent,
            user_session=user_session,
            details={
                "old_user_agent": user_session.user_agent,
                "new_user_agent": new_user_agent,
            },
        )

    def _handle_concurrent_session_alert(
        self, user: User, new_session: UserSession
    ) -> None:
        """Handle concurrent session anomaly alert."""
        active_sessions = UserSession.objects.active().for_user(user)

        SessionSecurityLog.log_event(
            user=user,
            event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            ip_address=new_session.ip_address,
            user_agent=new_session.user_agent,
            user_session=new_session,
            details={
                "concurrent_sessions": active_sessions.count(),
                "session_locations": list(
                    active_sessions.values_list("location", flat=True)
                ),
            },
        )

    def _detect_impossible_travel(self, ip_addresses: List[str]) -> bool:
        """
        Detect impossible travel between IP addresses.

        Args:
            ip_addresses: List of IP addresses

        Returns:
            True if impossible travel detected
        """
        # Simplified version - in production would calculate
        # geographic distances and time between accesses

        locations = [self.get_geolocation(ip) for ip in ip_addresses]
        countries = set(
            loc["country"] for loc in locations if loc and loc["country"] != "Unknown"
        )

        # If more than 2 different countries, flag as impossible travel
        return len(countries) > 2
