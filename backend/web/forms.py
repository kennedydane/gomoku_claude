"""
Forms for the web interface.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form for our User model."""
    
    email = forms.EmailField(
        required=False,
        help_text="Optional. We'll use this for account recovery."
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        """Save the user with the provided data."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user