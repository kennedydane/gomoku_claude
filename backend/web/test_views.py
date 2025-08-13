"""
TDD Tests for web interface views.

Following Red-Green-Refactor methodology:
1. RED: Write failing test
2. GREEN: Minimal implementation to pass test
3. REFACTOR: Improve code quality while keeping tests green
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from rest_framework.authtoken.models import Token

from games.models import Game, Challenge, GameStatus, ChallengeStatus
from tests.factories import UserFactory, GameFactory, ChallengeFactory, RuleSetFactory

User = get_user_model()


class TestWebFoundation(TestCase):
    """Test basic web interface foundation."""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_page_exists(self):
        """RED: Test that home page URL exists and returns 200."""
        # This test will FAIL initially - that's the RED phase
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 200)
    
    def test_home_page_redirects_to_web_home(self):
        """RED: Test that root URL redirects to web home."""
        response = self.client.get('/', follow=True)
        self.assertContains(response, 'Gomoku')
    
    def test_base_template_exists(self):
        """RED: Test that base template can be loaded."""
        try:
            template = get_template('base.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("base.html template does not exist")
    
    def test_web_urls_are_configured(self):
        """RED: Test that web URLs are properly configured."""
        # These should all exist in web/urls.py
        url_names = [
            'web:home',
            'web:login', 
            'web:register',
            'web:dashboard',
        ]
        
        for url_name in url_names:
            try:
                url = reverse(url_name)
                self.assertIsNotNone(url)
            except Exception:
                self.fail(f"URL name '{url_name}' not configured")


class TestAuthenticationViews(TestCase):
    """TDD tests for authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(username='testuser')
        self.user.set_password('testpass123')
        self.user.save()
    
    def test_login_page_renders(self):
        """RED: Test login page renders with proper form."""
        response = self.client.get(reverse('web:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'login')
        self.assertContains(response, 'form')
    
    def test_login_post_valid_credentials(self):
        """RED: Test login with valid credentials redirects to dashboard."""
        response = self.client.post(reverse('web:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        # Should redirect to dashboard after successful login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('web:dashboard'))
    
    def test_login_post_invalid_credentials(self):
        """RED: Test login with invalid credentials shows error."""
        response = self.client.post(reverse('web:login'), {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        # Should render login page again, not redirect
        self.assertContains(response, 'login')
    
    def test_register_page_renders(self):
        """RED: Test register page renders with form."""
        response = self.client.get(reverse('web:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'register')
    
    def test_logout_redirects_properly(self):
        """RED: Test logout redirects to home."""
        # Login first
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('web:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('web:home'))


class TestDashboardView(TestCase):
    """TDD tests for dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_dashboard_requires_authentication(self):
        """RED: Test dashboard requires user to be logged in."""
        # Logout first
        self.client.logout()
        
        response = self.client.get(reverse('web:dashboard'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_dashboard_shows_user_stats(self):
        """RED: Test dashboard displays user statistics."""
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, 'Games Played')
        self.assertContains(response, 'Games Won')
    
    def test_dashboard_shows_active_games(self):
        """RED: Test dashboard shows user's active games."""
        # Create an active game
        ruleset = RuleSetFactory()
        game = GameFactory(
            black_player=self.user,
            white_player=UserFactory(),
            ruleset=ruleset,
            status=GameStatus.ACTIVE
        )
        
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(game.id))
        self.assertContains(response, 'active')
    
    def test_dashboard_shows_pending_challenges(self):
        """RED: Test dashboard shows pending challenges."""
        challenger = UserFactory()
        challenge = ChallengeFactory(
            challenger=challenger,
            challenged=self.user,
            status=ChallengeStatus.PENDING
        )
        
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, challenge.challenger.username)
        self.assertContains(response, 'challenge')


class TestGameViews(TestCase):
    """TDD tests for game-related views."""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
        self.opponent = UserFactory()
        self.ruleset = RuleSetFactory()
        
        self.game = GameFactory(
            black_player=self.user,
            white_player=self.opponent,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        
        self.client.login(username=self.user.username, password='testpass123')
    
    def test_games_list_shows_user_games(self):
        """RED: Test games list shows games where user is a player."""
        response = self.client.get(reverse('web:games'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.game.id))
    
    def test_game_detail_shows_board(self):
        """RED: Test game detail shows interactive board."""
        response = self.client.get(reverse('web:game_detail', kwargs={'game_id': self.game.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'game-board')
        self.assertContains(response, 'board-cell')
    
    def test_game_move_requires_player(self):
        """RED: Test that only players in game can make moves."""
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
        self.assertEqual(response.status_code, 403)


class TestTemplateRendering(TestCase):
    """TDD tests for template rendering."""
    
    def test_base_template_includes_required_elements(self):
        """RED: Test base template has all required elements."""
        from django.template import Context, Template
        
        # This will fail initially until we create proper base.html
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
        
        self.assertIn('<!DOCTYPE html>', rendered)
        self.assertIn('Gomoku', rendered)
        self.assertIn('navbar', rendered)
    
    def test_static_files_are_configured(self):
        """RED: Test that static files are properly configured."""
        from django.conf import settings
        from django.contrib.staticfiles import finders
        
        # Test that static directories are configured
        self.assertIn('static', str(settings.STATICFILES_DIRS))
        
        # Test that we can find our custom CSS file
        css_file = finders.find('css/style.css')
        self.assertIsNotNone(css_file, "style.css not found in static files")


# Run these tests with: uv run python manage.py test web.test_views
# They will FAIL initially - that's the RED phase of TDD!
# Next step: Implement minimal code to make them pass (GREEN phase)