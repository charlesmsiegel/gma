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
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with additional fields."""

    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address.",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email address"}
        ),
    )

    display_name = forms.CharField(
        max_length=100,
        required=False,
        help_text="Optional. A display name for your profile.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter a display name (optional)",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "display_name", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Choose a username"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes and placeholders to password fields
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Enter your password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Confirm your password"}
        )

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


class EmailVerificationRegistrationForm(forms.Form):
    """
    Registration form with email verification integration for Issue #135.

    This form handles user registration with email verification,
    creating both the user and the email verification record.
    """

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter username"}
        ),
        help_text=(
            "Required. 150 characters or fewer. Unique username for your account."
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "type": "email",
                "placeholder": "Enter email address",
            }
        ),
        help_text="Required. Enter a valid email address for verification.",
    )

    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter password"}
        ),
        help_text="Required. Your password must contain at least 8 characters.",
    )

    password_confirm = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm password"}
        ),
        help_text="Required. Enter the same password as above for verification.",
    )

    display_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter display name (optional)",
            }
        ),
        help_text="Optional. A display name for your profile.",
    )

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter first name (optional)",
            }
        ),
        help_text="Optional. Your first name.",
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter last name (optional)"}
        ),
        help_text="Optional. Your last name.",
    )

    def clean_username(self):
        """Validate username uniqueness."""
        username = self.cleaned_data.get("username")
        if username and User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        """Validate email uniqueness (case-insensitive)."""
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower() if email else email

    def clean_password(self):
        """Validate password using Django's password validators."""
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        """Validate password confirmation."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        """
        Create user and email verification record.

        Returns:
            User: The created user instance
        """
        from users.models import EmailVerification
        from users.services import EmailVerificationService

        if not commit:
            raise ValueError("EmailVerificationRegistrationForm must be committed")

        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password"]
        display_name = self.cleaned_data.get("display_name")
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")

        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Set display_name to None if empty (for unique constraint)
            user.display_name = display_name if display_name else None
            user.email_verified = False  # Start unverified
            user.save()

            # Create email verification record
            verification = EmailVerification.create_for_user(user)

            # Update user's verification token field
            user.email_verification_token = verification.token
            user.email_verification_sent_at = verification.created_at
            user.save(
                update_fields=["email_verification_token", "email_verification_sent_at"]
            )

            # Send verification email
            service = EmailVerificationService()
            service.send_verification_email(user)

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
        from users.utils import authenticate_by_email_or_username

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate_by_email_or_username(
                self.request, username, password
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

    timezone = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Select your timezone for accurate time displays.",
    )

    theme = forms.ChoiceField(
        choices=User.THEME_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Choose your preferred theme for the interface",
        required=False,
    )

    def clean_theme(self):
        """Validate theme field, allowing None but not empty string."""
        theme = self.cleaned_data.get("theme")

        # If theme field is missing from form data entirely, that's OK
        if "theme" not in self.data:
            return None

        # If an empty string is explicitly provided, that's invalid
        if theme == "":
            raise ValidationError(
                "Select a valid choice. That choice is not one of the "
                "available choices."
            )

        # None is also invalid if explicitly provided in form data
        if theme is None and "theme" in self.data:
            raise ValidationError(
                "Select a valid choice. That choice is not one of the "
                "available choices."
            )

        return theme

    def __init__(self, *args, **kwargs):
        """Initialize form and populate timezone choices."""
        super().__init__(*args, **kwargs)

        # Common timezone choices - using Django-compatible timezone names
        timezone_choices = [
            ("UTC", "UTC"),
            ("America/New_York", "America/New_York"),
            ("America/Chicago", "America/Chicago"),
            ("America/Denver", "America/Denver"),
            ("America/Los_Angeles", "America/Los_Angeles"),
            ("Europe/London", "Europe/London"),
            ("Europe/Paris", "Europe/Paris"),
            ("Europe/Berlin", "Europe/Berlin"),
            ("Asia/Tokyo", "Asia/Tokyo"),
            ("Asia/Shanghai", "Asia/Shanghai"),
            ("Australia/Sydney", "Australia/Sydney"),
        ]

        self.fields["timezone"].choices = timezone_choices

        # Set initial value for theme field from current user
        if self.instance and hasattr(self.instance, "theme"):
            self.fields["theme"].initial = self.instance.theme

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

    def save(self, commit=True):
        """Save the form, including the theme field."""
        user = super().save(commit=False)

        # Set theme if provided in cleaned_data
        if self.cleaned_data.get("theme"):
            user.theme = self.cleaned_data["theme"]

        if commit:
            user.save()
        return user
