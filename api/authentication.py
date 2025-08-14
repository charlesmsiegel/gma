"""
Custom authentication and exception handling for the API.

This module provides custom authentication classes and exception handlers
to ensure proper HTTP status codes are returned for authentication failures.
"""

from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from django.contrib.auth.models import AnonymousUser


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns appropriate HTTP status codes:
    - Anonymous user + PermissionDenied (not CSRF) → 401 Unauthorized
    - CSRF failures → 403 Forbidden (security-related, not authentication)
    - Authenticated user + PermissionDenied → 403 Forbidden  
    - Everything else → original status code
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # Get the request from context to check user authentication status
        request = context.get('request')
        
        if request is not None:
            user = getattr(request, 'user', None)
            
            # For PermissionDenied exceptions, check if it's CSRF-related
            if isinstance(exc, PermissionDenied):
                # Check if this is a CSRF failure by examining the exception details
                exc_str = str(exc).lower()
                is_csrf_failure = 'csrf' in exc_str or 'csrf token' in exc_str
                
                # Only change to 401 for anonymous users if it's NOT a CSRF failure
                if user and isinstance(user, AnonymousUser) and not is_csrf_failure:
                    response.status_code = status.HTTP_401_UNAUTHORIZED
                # For CSRF failures or authenticated users, keep 403
                
            # Keep existing NotAuthenticated handling for completeness
            elif isinstance(exc, NotAuthenticated):
                response.status_code = status.HTTP_401_UNAUTHORIZED

    return response