from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Q

from games.models import Game, Challenge, GameStatus, ChallengeStatus
from users.models import User
from .forms import CustomUserCreationForm


class UserGamesMixin:
    """Mixin to provide user games query functionality."""
    
    def get_user_games_query(self, user):
        """Get Q object for filtering games where user is a player."""
        return Q(black_player=user) | Q(white_player=user)


class HomeView(TemplateView):
    """Home page view."""
    template_name = 'web/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gomoku'
        return context


class WebLoginView(LoginView):
    """Login view for web interface."""
    template_name = 'web/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('web:dashboard')


class WebLogoutView(LogoutView):
    """Logout view for web interface."""
    next_page = 'web:home'


class RegisterView(View):
    """User registration view."""
    template_name = 'web/register.html'
    form_class = CustomUserCreationForm
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('web:dashboard')
        return render(request, self.template_name, {'form': form})


class DashboardView(LoginRequiredMixin, UserGamesMixin, TemplateView):
    """Dashboard view for authenticated users."""
    template_name = 'web/dashboard.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User stats using mixin
        user_games_query = self.get_user_games_query(user)
        
        games_played = Game.objects.filter(user_games_query).count()
        games_won = Game.objects.filter(user_games_query, winner=user).count()
        
        # Active games with optimized queries
        active_games = Game.objects.select_related(
            'black_player', 'white_player', 'ruleset'
        ).filter(user_games_query, status=GameStatus.ACTIVE)
        
        # Pending challenges with optimized queries
        pending_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).filter(challenged=user, status=ChallengeStatus.PENDING)
        
        context.update({
            'games_played': games_played,
            'games_won': games_won,
            'active_games': active_games,
            'pending_challenges': pending_challenges,
        })
        return context


class GamesView(LoginRequiredMixin, UserGamesMixin, TemplateView):
    """List user's games."""
    template_name = 'web/games.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Use mixin and optimize queries
        user_games_query = self.get_user_games_query(user)
        user_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner', 'ruleset'
        ).filter(user_games_query).order_by('-created_at')
        
        context['games'] = user_games
        return context


class GameDetailView(LoginRequiredMixin, TemplateView):
    """Game detail view with interactive board."""
    template_name = 'web/game_detail.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game_id = kwargs.get('game_id')
        
        try:
            # Optimize with select_related
            game = Game.objects.select_related(
                'black_player', 'white_player', 'winner', 'ruleset'
            ).get(id=game_id)
            
            # Only allow players to view game
            if self.request.user not in [game.black_player, game.white_player]:
                context['error'] = 'Access denied'
                return context
                
            context['game'] = game
        except Game.DoesNotExist:
            context['error'] = 'Game not found'
        except ValueError:
            context['error'] = 'Invalid game ID'
            
        return context


class GameMoveView(LoginRequiredMixin, View):
    """Handle game moves via POST."""
    login_url = 'web:login'
    
    def post(self, request, game_id):
        try:
            # Optimize query
            game = Game.objects.select_related(
                'black_player', 'white_player'
            ).get(id=game_id)
            
            # Only allow players to make moves
            if request.user not in [game.black_player, game.white_player]:
                return render(request, 'web/error.html', {
                    'error': 'Access denied'
                }, status=403)
                
            # Game move logic would go here
            # For now, return success
            return redirect('web:game_detail', game_id=game_id)
            
        except Game.DoesNotExist:
            return render(request, 'web/error.html', {
                'error': 'Game not found'
            }, status=404)
        except ValueError:
            return render(request, 'web/error.html', {
                'error': 'Invalid game ID'
            }, status=400)
