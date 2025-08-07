"""
Forms for user authentication and registration.
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
        """Validate email is unique."""
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        """Save user with email and display_name."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        display_name = self.cleaned_data.get("display_name")
        if display_name:
            user.display_name = display_name
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
            # Try authenticating with username first
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )

            # If that fails and username looks like email, try finding user by email
            if self.user_cache is None and "@" in username:
                try:
                    user = User.objects.get(email=username)
                    self.user_cache = authenticate(
                        self.request, username=user.username, password=password
                    )
                except User.DoesNotExist:
                    pass

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
