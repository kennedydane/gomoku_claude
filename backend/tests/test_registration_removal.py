"""
Tests to verify registration functionality has been removed.
Following TDD principles - these tests should pass after registration is removed.
"""

import pytest
from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.template.loader import TemplateDoesNotExist, get_template
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRegistrationRemoval:
    """Test that registration functionality has been completely removed."""

    def test_registration_url_returns_404(self, client):
        """Test that the registration URL no longer exists."""
        # This should return 404 after registration is removed
        response = client.get('/register/')
        assert response.status_code == 404

    def test_registration_url_name_does_not_exist(self):
        """Test that the 'web:register' URL name no longer exists."""
        with pytest.raises(NoReverseMatch):
            reverse('web:register')

    def test_registration_post_returns_404(self, client):
        """Test that POST to registration endpoint returns 404."""
        response = client.post('/register/', {
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })
        assert response.status_code == 404

    def test_register_view_does_not_exist(self):
        """Test that RegisterView class has been removed from views module."""
        from web import views
        assert not hasattr(views, 'RegisterView')

    def test_custom_user_creation_form_does_not_exist(self):
        """Test that CustomUserCreationForm has been removed."""
        try:
            from web.forms import CustomUserCreationForm
            # If import succeeds, the test should fail
            assert False, "CustomUserCreationForm should have been removed"
        except ImportError:
            # This is expected after removal
            pass

    def test_register_template_does_not_exist(self):
        """Test that register.html template has been removed."""
        with pytest.raises(TemplateDoesNotExist):
            get_template('web/register.html')

    def test_users_can_only_be_created_via_admin_or_management(self, client):
        """Test that users can only be created through admin interface or management commands."""
        # Verify no web-based registration is possible
        initial_user_count = User.objects.count()
        
        # Try various potential registration endpoints
        registration_attempts = [
            '/register/',
            '/signup/',
            '/api/register/',
            '/api/auth/register/',
        ]
        
        for url in registration_attempts:
            response = client.get(url)
            assert response.status_code in [404, 405], f"URL {url} should not be accessible"
            
            response = client.post(url, {
                'username': 'testuser',
                'password': 'testpass123'
            })
            assert response.status_code in [404, 405], f"POST to {url} should not be accessible"
        
        # Verify no users were created through web interface
        assert User.objects.count() == initial_user_count

    def test_login_still_works(self, client, django_user_model):
        """Test that login functionality remains intact after registration removal."""
        # Create a user directly (simulating admin creation)
        from faker import Faker
        fake = Faker()
        test_username = fake.user_name()
        user = django_user_model.objects.create_user(
            username=test_username,
            password='testpass123'
        )
        
        # Test login still works
        response = client.post('/login/', {
            'username': test_username,
            'password': 'testpass123'
        })
        
        # Should redirect to dashboard on successful login
        assert response.status_code == 302
        assert '/dashboard/' in response.url

    def test_navigation_does_not_include_registration_links(self, client, django_user_model):
        """Test that navigation templates don't include registration links."""
        # Test home page doesn't have registration links
        response = client.get('/home/')
        assert response.status_code == 200
        content = response.content.decode()
        
        # Should not contain registration links
        registration_terms = [
            'register',
            'sign up',
            'signup',
            'create account',
            'web:register',
            '/register/'
        ]
        
        for term in registration_terms:
            assert term.lower() not in content.lower(), f"Found '{term}' in navigation"

    def test_login_page_does_not_link_to_registration(self, client):
        """Test that login page doesn't have registration links."""
        response = client.get('/login/')
        assert response.status_code == 200
        content = response.content.decode()
        
        # Should not contain registration links
        registration_terms = [
            'register',
            'sign up',
            'signup',
            'create account',
            'web:register',
            '/register/'
        ]
        
        for term in registration_terms:
            assert term.lower() not in content.lower(), f"Found '{term}' in login page"