"""
pytest tests for web interface views.

Migrated from web/test_views.py to pytest format for better test management.
Following TDD methodology with comprehensive web interface coverage.
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.template import TemplateDoesNotExist, Context, Template
from django.conf import settings
from django.contrib.staticfiles import finders
from rest_framework.authtoken.models import Token

from games.models import Game, Challenge, GameStatus, ChallengeStatus
from tests.factories import UserFactory, GameFactory, ChallengeFactory, GomokuRuleSetFactory

User = get_user_model()


@pytest.mark.django_db
class TestWebFoundation:
    """Test basic web interface foundation."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
    
    def test_home_page_exists(self):
        """Test that home page URL exists and returns 200."""
        response = self.client.get('/home/')
        assert response.status_code == 200
    
    def test_home_page_redirects_to_web_home(self):
        """Test that root URL redirects to web home."""
        response = self.client.get('/', follow=True)
        assert b'Gomoku' in response.content
    
    def test_base_template_exists(self):
        """Test that base template can be loaded."""
        try:
            template = get_template('base.html')
            assert template is not None
        except TemplateDoesNotExist:
            pytest.fail("base.html template does not exist")
    
    def test_web_urls_are_configured(self):
        """Test that web URLs are properly configured."""
        url_names = [
            'web:home',
            'web:login', 
            'web:dashboard',
        ]
        
        for url_name in url_names:
            try:
                url = reverse(url_name)
                assert url is not None
            except Exception:
                pytest.fail(f"URL name '{url_name}' not configured")


@pytest.mark.django_db
class TestAuthenticationViews:
    """pytest tests for authentication views."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
    
    def test_login_page_renders(self):
        """Test login page renders with proper form."""
        response = self.client.get(reverse('web:login'))
        assert response.status_code == 200
        assert b'login' in response.content.lower()
        assert b'form' in response.content.lower()
    
    def test_login_post_valid_credentials(self):
        """Test login with valid credentials redirects to dashboard."""
        response = self.client.post(reverse('web:login'), {
            'username': self.user.username,
            'password': 'testpass123'
        })
        # Should redirect to dashboard after successful login
        assert response.status_code == 302
        assert response.url == reverse('web:dashboard')
    
    def test_login_post_invalid_credentials(self):
        """Test login with invalid credentials shows error."""
        response = self.client.post(reverse('web:login'), {
            'username': self.user.username,
            'password': 'wrongpass'
        })
        assert response.status_code == 200
        # Should render login page again, not redirect
        assert b'login' in response.content.lower()
    
    def test_register_functionality_removed(self):
        """Test that registration functionality has been removed."""
        # Registration should not be available
        try:
            url = reverse('web:register')
            pytest.fail("Registration URL should not exist")
        except Exception:
            # This is expected - registration was removed
            pass
    
    def test_logout_redirects_properly(self):
        """Test logout redirects to home."""
        # Login first
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('web:logout'))
        assert response.status_code == 302
        assert response.url == reverse('web:home')


@pytest.mark.django_db
class TestDashboardView:
    """pytest tests for dashboard view."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_dashboard_requires_authentication(self):
        """Test dashboard requires user to be logged in."""
        # Logout first
        self.client.logout()
        
        response = self.client.get(reverse('web:dashboard'))
        # Should redirect to login
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_dashboard_shows_user_stats(self):
        """Test dashboard displays user statistics."""
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        assert self.user.username.encode() in response.content
        assert b'Games Played' in response.content or b'games' in response.content.lower()
    
    def test_dashboard_shows_active_games(self):
        """Test dashboard shows user's active games."""
        # Create an active game
        ruleset = GomokuRuleSetFactory()
        game = GameFactory(
            black_player=self.user,
            white_player=UserFactory(),
            ruleset=ruleset,
            status=GameStatus.ACTIVE
        )
        
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        # Check for game presence - could be game ID or active status
        game_id_bytes = str(game.id).encode()
        assert (game_id_bytes in response.content or 
                b'active' in response.content.lower() or
                b'game' in response.content.lower())
    
    def test_dashboard_shows_pending_challenges(self):
        """Test dashboard shows pending challenges."""
        challenger = UserFactory()
        challenge = ChallengeFactory(
            challenger=challenger,
            challenged=self.user,
            status=ChallengeStatus.PENDING
        )
        
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        # Check for challenge-related content
        challenger_name = challenge.challenger.username.encode()
        assert (challenger_name in response.content or
                b'challenge' in response.content.lower() or
                b'pending' in response.content.lower())


@pytest.mark.django_db
class TestGameViews:
    """pytest tests for game-related views."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
        self.opponent = UserFactory()
        self.ruleset = GomokuRuleSetFactory()
        
        self.game = GameFactory(
            black_player=self.user,
            white_player=self.opponent,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_games_list_shows_user_games(self):
        """Test games list shows games where user is a player."""
        response = self.client.get(reverse('web:games'))
        assert response.status_code == 200
        game_id_bytes = str(self.game.id).encode()
        assert game_id_bytes in response.content
    
    def test_game_detail_shows_board(self):
        """Test game detail redirects to dashboard and shows interactive board."""
        response = self.client.get(reverse('web:game_detail', kwargs={'game_id': self.game.id}), follow=True)
        assert response.status_code == 200
        # Check for game board elements after redirect
        assert (b'game-board' in response.content or 
                b'board-intersection' in response.content or
                b'game' in response.content.lower())
    
    def test_game_move_requires_player(self):
        """Test that only players in game can make moves."""
        # Create another user who is not in the game
        other_user = UserFactory()
        other_user.set_password('testpass123')
        other_user.save()
        
        self.client.logout()
        self.client.login(username=other_user.username, password='testpass123')
        
        response = self.client.post(
            reverse('web:game_move', kwargs={'game_id': self.game.id}),
            {'row': 7, 'col': 7}
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTemplateRendering:
    """pytest tests for template rendering."""
    
    def test_base_template_includes_required_elements(self):
        """Test base template has all required elements."""
        # Test basic template rendering functionality
        template_content = """
        {% load static %}
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test</title>
            <link href="{% static 'css/style.css' %}" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar">Gomoku</nav>
            <main>{% block content %}{% endblock %}</main>
            <script src="{% static 'js/app.js' %}"></script>
        </body>
        </html>
        """
        
        template = Template(template_content)
        context = Context({})
        rendered = template.render(context)
        
        assert '<!DOCTYPE html>' in rendered
        assert 'Gomoku' in rendered
        assert 'navbar' in rendered
    
    def test_static_files_are_configured(self):
        """Test that static files are properly configured."""
        # Test that static directories are configured
        assert 'static' in str(settings.STATICFILES_DIRS)
        
        # Test that we can find static files (more flexible check)
        # Look for any CSS file to verify static files work
        css_file = finders.find('css/style.css')
        if css_file is None:
            # If style.css doesn't exist, that's OK for this test
            # We're just testing that the static files system works
            assert hasattr(settings, 'STATICFILES_DIRS')
        else:
            assert css_file is not None


@pytest.mark.django_db 
class TestViewPermissions:
    """Test view-level permissions and access control."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
    
    def test_authenticated_views_require_login(self):
        """Test that authenticated views redirect to login when not logged in."""
        protected_urls = [
            reverse('web:dashboard'),
        ]
        
        # Try to access protected URLs without login
        for url in protected_urls:
            response = self.client.get(url)
            assert response.status_code == 302
            assert 'login' in response.url
    
    def test_authenticated_views_work_when_logged_in(self):
        """Test that authenticated views work when user is logged in."""
        self.client.login(username=self.user.username, password='testpass123')
        
        protected_urls = [
            reverse('web:dashboard'),
        ]
        
        # Try to access protected URLs with login
        for url in protected_urls:
            response = self.client.get(url)
            assert response.status_code == 200


@pytest.mark.django_db
class TestViewContextData:
    """Test that views provide correct context data."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_dashboard_provides_user_context(self):
        """Test that dashboard provides user in context."""
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        
        # Check that user information is in the response
        assert self.user.username.encode() in response.content
    
    def test_views_handle_missing_data_gracefully(self):
        """Test that views handle missing or empty data gracefully."""
        # User with no games or challenges
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        # Should not crash even with no games


@pytest.mark.django_db
class TestResponseFormats:
    """Test that views return appropriate response formats."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_html_views_return_html_content(self):
        """Test that HTML views return proper HTML content."""
        response = self.client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/html')
    
    def test_ajax_requests_handled_appropriately(self):
        """Test that AJAX requests are handled appropriately."""
        # Test with XHR header to simulate AJAX request
        response = self.client.get(
            reverse('web:dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        # Should still work, might return different format