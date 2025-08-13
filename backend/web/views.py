from typing import Optional, Union, Dict, Any
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Q
from django.http import JsonResponse

from games.models import Game, Challenge, GameStatus, ChallengeStatus, RuleSet
from games.services import GameService
from core.exceptions import InvalidMoveError, GameStateError, PlayerError
from users.models import User
from .forms import CustomUserCreationForm
from .models import Friendship, FriendshipStatus

try:
    from django_eventstream import send_event
    HAS_EVENTSTREAM = True
except ImportError:
    HAS_EVENTSTREAM = False
    send_event = None

from loguru import logger


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


class WebLogoutView(View):
    """Logout view for web interface."""
    
    def get(self, request):
        """Handle GET logout with immediate logout."""
        if request.user.is_authenticated:
            from django.contrib.auth import logout
            logout(request)
        return redirect('web:home')
    
    def post(self, request):
        """Handle POST logout."""
        if request.user.is_authenticated:
            from django.contrib.auth import logout
            logout(request)
        return redirect('web:home')


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
        
        # Pending challenges with optimized queries (received challenges)
        from django.utils import timezone
        pending_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenged=user, 
            status=ChallengeStatus.PENDING,
            expires_at__gt=timezone.now()  # Only non-expired challenges
        )
        
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
    
    def is_htmx_request(self, request):
        """Check if request is from HTMX."""
        return request.headers.get('HX-Request') == 'true'
    
    def post(self, request, game_id):
        try:
            # Get row and col from request
            row = int(request.POST.get('row', -1))
            col = int(request.POST.get('col', -1))
            
            # Optimize query
            game = Game.objects.select_related(
                'black_player', 'white_player', 'ruleset'
            ).get(id=game_id)
            
            # Only allow players to make moves
            if request.user not in [game.black_player, game.white_player]:
                if self.is_htmx_request(request):
                    return render(request, 'web/partials/error_message.html', {
                        'error': 'Access denied - you are not a player in this game'
                    }, status=403)
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Access denied'}, status=403)
                return render(request, 'web/error.html', {
                    'error': 'Access denied'
                }, status=403)
            
            # Make the move using GameService
            try:
                move = GameService.make_move(game, request.user.id, row, col)
                
                # Refresh game from database to get updated state
                game.refresh_from_db()
                
                # Send SSE event to notify other player of the move
                logger.info(f"🎮 MOVE: Processing move by {request.user.username} in game {game.id}")
                
                if HAS_EVENTSTREAM:
                    # Determine which player should receive the notification
                    if request.user == game.black_player:
                        notify_user_id = game.white_player.id
                        notify_username = game.white_player.username
                    else:
                        notify_user_id = game.black_player.id  
                        notify_username = game.black_player.username
                    
                    logger.info(f"📡 SSE: Will notify user {notify_username} (ID: {notify_user_id}) about move")
                    
                    try:
                        # Send HTML fragment for HTMX SSE
                        from django.middleware.csrf import get_token
                        csrf_token = get_token(request)
                        logger.debug(f"🔐 CSRF: Token generated for SSE: {csrf_token[:10]}..." if csrf_token else "🔐 CSRF: No token generated")
                        
                        response = render(request, 'web/partials/game_board.html', {
                            'game': game,
                            'csrf_token': csrf_token
                        })
                        board_html = response.content.decode('utf-8').strip()
                        
                        # Remove newlines for SSE compatibility 
                        # SSE protocol treats consecutive newlines as end-of-event markers
                        # so we need to strip them to prevent truncation
                        board_html_sse = ' '.join(board_html.split())
                        
                        # Log HTML snippet for debugging
                        logger.debug(f"📄 HTML: Generated board HTML ({len(board_html)} chars): {board_html[:100]}...")
                        logger.debug(f"📄 SSE HTML: Stripped for SSE ({len(board_html_sse)} chars): {board_html_sse[:100]}...")
                        logger.debug(f"🔍 HTML Check: Contains CSRF token: {'X-CSRFToken' in board_html_sse}")
                        
                        channel = f'user-{notify_user_id}'
                        event_name = 'game_move'
                        logger.info(f"📤 SSE: Sending event '{event_name}' to channel '{channel}'")
                        
                        # Send the newline-stripped HTML content for HTMX to process
                        send_event(channel, event_name, board_html_sse)
                        logger.success(f"✅ SSE: Event sent successfully to {notify_username}")
                        
                    except Exception as e:
                        # Don't fail the request if SSE fails
                        logger.error(f"❌ SSE: Failed to send event to {notify_username}: {type(e).__name__}: {str(e)}")
                        import traceback
                        logger.debug(f"📋 SSE: Full traceback: {traceback.format_exc()}")
                else:
                    logger.warning(f"⚠️  SSE: django-eventstream not available, skipping real-time update")
                
                # Return HTML fragment for HTMX requests
                if self.is_htmx_request(request):
                    from django.middleware.csrf import get_token
                    return render(request, 'web/partials/game_board.html', {
                        'game': game,
                        'csrf_token': get_token(request)
                    })
                
                # Return JSON response for AJAX requests
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'board_state': game.board_state,
                        'current_player': game.current_player,
                        'status': game.status,
                        'move': {
                            'row': row,
                            'col': col,
                            'player': move.player.username if hasattr(move, 'player') else request.user.username
                        }
                    })
                
                # For non-AJAX requests, redirect to game detail
                return redirect('web:game_detail', game_id=game_id)
                
            except PlayerError as e:
                if self.is_htmx_request(request):
                    return render(request, 'web/partials/error_message.html', {
                        'error': str(e)
                    }, status=403)
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': str(e)}, status=403)
                return render(request, 'web/error.html', {
                    'error': str(e)
                }, status=403)
            except (InvalidMoveError, GameStateError) as e:
                if self.is_htmx_request(request):
                    return render(request, 'web/partials/error_message.html', {
                        'error': str(e)
                    }, status=400)
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': str(e)}, status=400)
                return render(request, 'web/error.html', {
                    'error': str(e)
                }, status=400)
            
        except Game.DoesNotExist:
            if self.is_htmx_request(request):
                return render(request, 'web/partials/error_message.html', {
                    'error': 'Game not found'
                }, status=404)
            elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Game not found'}, status=404)
            return render(request, 'web/error.html', {
                'error': 'Game not found'
            }, status=404)
        except (ValueError, TypeError):
            if self.is_htmx_request(request):
                return render(request, 'web/partials/error_message.html', {
                    'error': 'Invalid move coordinates'
                }, status=400)
            elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Invalid move coordinates'}, status=400)
            return render(request, 'web/error.html', {
                'error': 'Invalid move coordinates'
            }, status=400)


# Friend System Views

from django.http import JsonResponse
from django.core.exceptions import ValidationError


class FriendAPIViewMixin:
    """Mixin providing common functionality for Friend API views."""
    
    def json_response(self, data: Union[Dict[str, Any], list], status: int = 200) -> JsonResponse:
        """Create a JSON response."""
        # Set safe=False for non-dict data (lists, etc.)
        safe = isinstance(data, dict)
        return JsonResponse(data, status=status, safe=safe)
    
    def json_error(self, message: str, status: int = 400) -> JsonResponse:
        """Create a JSON error response."""
        return JsonResponse({'error': message}, status=status)
    
    def get_user_or_404(self, username: str) -> Optional[User]:
        """Get user by username or return None if not found."""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None


class SendFriendRequestView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Send a friend request to another user."""
    login_url = 'web:login'
    
    def post(self, request):
        username = request.POST.get('username')
        if not username:
            return self.json_error('Username is required', 400)
        
        # Check if trying to befriend self
        if username == request.user.username:
            return self.json_error('Cannot send friend request to yourself', 400)
        
        # Check if user exists
        addressee = self.get_user_or_404(username)
        if not addressee:
            return self.json_error('User not found', 404)
        
        # Check if friendship already exists
        existing = Friendship.objects.filter(
            Q(requester=request.user, addressee=addressee) |
            Q(requester=addressee, addressee=request.user)
        ).first()
        
        if existing:
            return self.json_error('Friend request already exists', 400)
        
        # Create friendship
        try:
            friendship = Friendship.objects.create(
                requester=request.user,
                addressee=addressee
            )
            return self.json_response({
                'message': 'Friend request sent',
                'friendship_id': friendship.id
            }, 201)
        except ValidationError as e:
            return self.json_error(str(e), 400)


class RespondFriendRequestView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Respond to a friend request (accept/reject)."""
    login_url = 'web:login'
    
    def post(self, request, friendship_id):
        action = request.POST.get('action')
        if action not in ['accept', 'reject']:
            return self.json_error('Invalid action', 400)
        
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            return self.json_error('Friend request not found', 404)
        
        # Check if user is the addressee
        if friendship.addressee != request.user:
            return self.json_error('Access denied', 403)
        
        # Check if status is pending
        if friendship.status != FriendshipStatus.PENDING:
            return self.json_error('Friend request is no longer pending', 400)
        
        # Update status
        if action == 'accept':
            friendship.status = FriendshipStatus.ACCEPTED
        else:
            friendship.status = FriendshipStatus.REJECTED
        
        friendship.save()
        
        return self.json_response({
            'message': f'Friend request {action}ed',
            'status': friendship.status
        })


class FriendsListView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Get user's friends list."""
    login_url = 'web:login'
    
    def get(self, request):
        friends = Friendship.objects.get_friends(request.user)
        friends_data = [{'username': friend.username} for friend in friends]
        return self.json_response(friends_data)


class PendingRequestsView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Get user's pending friend requests."""
    login_url = 'web:login'
    
    def get(self, request):
        pending = Friendship.objects.get_pending_requests(request.user)
        requests_data = [{
            'id': req.id,
            'requester': {'username': req.requester.username},
            'created_at': req.created_at.isoformat()
        } for req in pending]
        return self.json_response(requests_data)


class SearchUsersView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Search for users to befriend."""
    login_url = 'web:login'
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return self.json_response([])
        
        # Search users by username (excluding self)
        users = User.objects.filter(
            username__icontains=query
        ).exclude(id=request.user.id)[:10]
        
        users_data = [{'username': user.username} for user in users]
        return self.json_response(users_data)


class FriendsPageView(LoginRequiredMixin, TemplateView):
    """Web page for friends management."""
    template_name = 'web/friends.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get friends and pending requests
        friends = Friendship.objects.get_friends(user)
        pending_requests = Friendship.objects.get_pending_requests(user)
        
        context.update({
            'friends': friends,
            'pending_requests': pending_requests,
        })
        return context


# Challenge System Views

class ChallengeFriendView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Send a game challenge to a friend."""
    login_url = 'web:login'
    
    def post(self, request):
        username = request.POST.get('username')
        ruleset_id = request.POST.get('ruleset_id')
        
        if not username or not ruleset_id:
            return self.json_error('Username and ruleset are required', 400)
        
        # Check if trying to challenge self
        if username == request.user.username:
            return self.json_error('Cannot challenge yourself', 400)
        
        # Check if user exists
        challenged_user = self.get_user_or_404(username)
        if not challenged_user:
            return self.json_error('User not found', 404)
        
        # Check if they are friends
        is_friend = Friendship.objects.filter(
            Q(requester=request.user, addressee=challenged_user, status=FriendshipStatus.ACCEPTED) |
            Q(requester=challenged_user, addressee=request.user, status=FriendshipStatus.ACCEPTED)
        ).exists()
        
        if not is_friend:
            return self.json_error('You can only challenge friends', 400)
        
        # Check if ruleset exists
        try:
            ruleset = RuleSet.objects.get(id=ruleset_id)
        except RuleSet.DoesNotExist:
            return self.json_error('Invalid ruleset', 400)
        
        # Check for existing pending challenge
        existing = Challenge.objects.filter(
            challenger=request.user,
            challenged=challenged_user,
            status=ChallengeStatus.PENDING
        ).first()
        
        if existing:
            return self.json_error('You already have a pending challenge with this user', 400)
        
        # Create challenge
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            challenge = Challenge.objects.create(
                challenger=request.user,
                challenged=challenged_user,
                ruleset=ruleset,
                expires_at=timezone.now() + timedelta(minutes=5)  # 5 minute expiry
            )
            
            return self.json_response({
                'success': True,
                'message': f'Challenge sent to {username}',
                'challenge_id': str(challenge.id)
            }, 200)
            
        except Exception as e:
            return self.json_error(f'Failed to create challenge: {str(e)}', 500)


class RespondChallengeView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Respond to a game challenge (accept/reject)."""
    login_url = 'web:login'
    
    def post(self, request, challenge_id):
        action = request.POST.get('action')
        if action not in ['accept', 'reject']:
            return self.json_error('Invalid action', 400)
        
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            return self.json_error('Challenge not found', 404)
        
        # Check if user is the challenged party
        if challenge.challenged != request.user:
            return self.json_error('Access denied', 403)
        
        # Check if challenge is still pending
        if challenge.status != ChallengeStatus.PENDING:
            return self.json_error('Challenge is no longer pending', 400)
        
        # Check if challenge is expired
        from django.utils import timezone
        if timezone.now() > challenge.expires_at:
            challenge.status = ChallengeStatus.EXPIRED
            challenge.save()
            return self.json_error('Challenge has expired', 400)
        
        # Handle response
        from django.utils import timezone
        challenge.responded_at = timezone.now()
        
        if action == 'accept':
            challenge.status = ChallengeStatus.ACCEPTED
            challenge.save()
            
            # Create game
            try:
                import random
                
                # Randomly assign colors
                if random.choice([True, False]):
                    black_player = challenge.challenger
                    white_player = challenge.challenged
                else:
                    black_player = challenge.challenged
                    white_player = challenge.challenger
                
                game = Game.objects.create(
                    black_player=black_player,
                    white_player=white_player,
                    ruleset=challenge.ruleset,
                    status=GameStatus.ACTIVE
                )
                game.initialize_board()
                game.save()
                
                # For HTMX requests, return HTML that redirects to the game
                if request.headers.get('HX-Request'):
                    response = render(request, 'web/partials/challenge_response.html', {
                        'success': True,
                        'message': 'Challenge accepted! Game created.',
                        'redirect_url': f'/games/{game.id}/'
                    })
                    response['HX-Redirect'] = f'/games/{game.id}/'
                    return response
                
                return self.json_response({
                    'success': True,
                    'message': 'Challenge accepted! Game created.',
                    'game_id': str(game.id),
                    'game_url': f'/games/{game.id}/'
                })
                
            except Exception as e:
                if request.headers.get('HX-Request'):
                    return render(request, 'web/partials/challenge_response.html', {
                        'error': f'Failed to create game: {str(e)}'
                    }, status=500)
                return self.json_error(f'Failed to create game: {str(e)}', 500)
        
        else:  # reject
            challenge.status = ChallengeStatus.REJECTED
            challenge.save()
            
            # For HTMX requests, return empty div (challenge disappears)
            if request.headers.get('HX-Request'):
                return render(request, 'web/partials/challenge_response.html', {
                    'success': True,
                    'message': 'Challenge rejected',
                    'hide_challenge': True
                })
            
            return self.json_response({
                'success': True,
                'message': 'Challenge rejected'
            })


class RulesetsListView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Get available rulesets for challenge creation."""
    login_url = 'web:login'
    
    def get(self, request):
        """Return list of available rulesets."""
        rulesets = RuleSet.objects.all().order_by('board_size', 'name')
        
        rulesets_data = [{
            'id': ruleset.id,
            'name': ruleset.name,
            'description': ruleset.description,
            'board_size': ruleset.board_size,
            'allow_overlines': ruleset.allow_overlines
        } for ruleset in rulesets]
        
        return self.json_response(rulesets_data)
