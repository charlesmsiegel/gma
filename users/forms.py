"""
Forms for user authentication and registration.

Security Notes:
- For production deployment, consider implementing rate limiting for login attempts
  to prevent brute force attacks. Recommended options:
  * django-ratelimit: https://django-ratelimit.readthedocs.io/
  * django-axes: https://django-axes.readthedocs.io/
  * Cloudflare or nginx-based rate limiting
- Current implementation uses secure error messages that don't reveal whether
  a username/email exists, following security best practices
"""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with additional fields."""

    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address.",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    display_name = forms.CharField(
        max_length=100,
        required=False,
        help_text="Optional. A display name for your profile.",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "display_name", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields["password1"].widget.attrs["class"] = "form-control"
        self.fields["password2"].widget.attrs["class"] = "form-control"

    def clean_email(self):
        """Validate email is unique (case-insensitive)."""
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        """Save user with email and display_name."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        display_name = self.cleaned_data.get("display_name")
        # Set display_name to None if empty (for unique constraint)
        user.display_name = display_name if display_name else None
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(forms.Form):
    """Authentication form that allows login with email or username."""

    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username or Email",
            }
        ),
        label="Username or Email",
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "Please enter a correct username/email and password. Note that both "
            "fields may be case-sensitive."
        ),
        "inactive": "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        """Initialize form with request."""
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        """Authenticate user with email or username."""
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            # Check if input looks like email and try to get user by email first
            if "@" in username:
                try:
                    user = User.objects.get(email__iexact=username)
                    # Use the found user's username for authentication
                    self.user_cache = authenticate(
                        self.request, username=user.username, password=password
                    )
                except User.DoesNotExist:
                    # Fall back to regular username authentication
                    self.user_cache = authenticate(
                        self.request, username=username, password=password
                    )
            else:
                # Input is likely a username, authenticate directly
                self.user_cache = authenticate(
                    self.request, username=username, password=password
                )

            if self.user_cache is None:
                raise ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """Check if user is allowed to log in."""
        if not user.is_active:
            raise ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )

    def get_user(self):
        """Return authenticated user."""
        return self.user_cache


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information."""

    # Common timezone choices for dropdown
    TIMEZONE_CHOICES = [
        ("UTC", "UTC (Coordinated Universal Time)"),
        ("America/New_York", "America/New_York (Eastern Time)"),
        ("America/Chicago", "America/Chicago (Central Time)"),
        ("America/Denver", "America/Denver (Mountain Time)"),
        ("America/Los_Angeles", "America/Los_Angeles (Pacific Time)"),
        ("America/Phoenix", "America/Phoenix (Arizona Time)"),
        ("America/Anchorage", "America/Anchorage (Alaska Time)"),
        ("Pacific/Honolulu", "Pacific/Honolulu (Hawaii Time)"),
        ("Europe/London", "Europe/London (GMT/BST)"),
        ("Europe/Paris", "Europe/Paris (CET/CEST)"),
        ("Europe/Berlin", "Europe/Berlin (CET/CEST)"),
        ("Europe/Rome", "Europe/Rome (CET/CEST)"),
        ("Europe/Madrid", "Europe/Madrid (CET/CEST)"),
        ("Europe/Stockholm", "Europe/Stockholm (CET/CEST)"),
        ("Asia/Tokyo", "Asia/Tokyo (Japan Standard Time)"),
        ("Asia/Shanghai", "Asia/Shanghai (China Standard Time)"),
        ("Asia/Kolkata", "Asia/Kolkata (India Standard Time)"),
        ("Australia/Sydney", "Australia/Sydney (AEST/AEDT)"),
        ("Australia/Melbourne", "Australia/Melbourne (AEST/AEDT)"),
        ("Australia/Perth", "Australia/Perth (AWST)"),
    ]

    timezone = forms.CharField(
        max_length=50,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select your timezone for accurate time displays.",
    )

    class Meta:
        model = User
        fields = ("display_name", "timezone")
        widgets = {
            "display_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional display name",
                }
            ),
        }
        help_texts = {
            "display_name": (
                "Optional. A display name for your profile. "
                "Leave blank to use your username."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for the timezone field
        choices = self.TIMEZONE_CHOICES

        # If timezone is not in our choices, add it as a custom option
        if self.instance and self.instance.timezone:
            timezone_values = [choice[0] for choice in self.TIMEZONE_CHOICES]
            if self.instance.timezone not in timezone_values:
                # Add current timezone as first choice if it's not in our common list
                custom_choice = (
                    self.instance.timezone,
                    f"{self.instance.timezone} (Custom)",
                )
                choices = [custom_choice] + self.TIMEZONE_CHOICES

        self.fields["timezone"].widget.choices = choices

    def clean_display_name(self):
        """Validate display_name uniqueness (case-insensitive, excluding self)."""
        display_name = self.cleaned_data.get("display_name")

        # Convert empty string to None for database unique constraint
        if not display_name:
            return None

        # Check for uniqueness, excluding current user
        queryset = User.objects.filter(display_name__iexact=display_name)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError("A user with this display name already exists.")

        return display_name

    def clean_timezone(self):
        """Validate timezone using the model validator."""
        timezone = self.cleaned_data.get("timezone")
        if timezone:
            # Use the model's timezone validator
            from .models.user import validate_timezone

            try:
                validate_timezone(timezone)
            except ValidationError as e:
                # Re-raise the validation error with proper message handling
                raise ValidationError(str(e))
        return timezone
