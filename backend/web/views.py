from typing import Optional, Union, Dict, Any
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, RedirectView
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


def send_structured_sse_event(user_id, event_type, content, metadata=None):
    """
    Send a structured SSE event with optional metadata for better client routing.
    
    Args:
        user_id: Target user ID
        event_type: Event type (game_move, dashboard_update, etc.)
        content: HTML content or data to send
        metadata: Optional dictionary with additional routing/context info
    """
    if not HAS_EVENTSTREAM or not send_event:
        logger.warning("⚠️  SSE: django-eventstream not available")
        return False
        
    channel = f'user-{user_id}'
    
    # Add optional metadata headers for advanced client-side routing
    if metadata:
        # For now, we keep it simple and just log metadata
        # Future enhancement could embed metadata in the event data
        logger.debug(f"📋 SSE: Event metadata for {event_type}: {metadata}")
    
    try:
        send_event(channel, event_type, content, json_encode=False)
        logger.info(f"📤 SSE: Event '{event_type}' sent to user-{user_id} (channel: {channel})")
        return True
    except Exception as e:
        logger.error(f"❌ SSE: Failed to send {event_type} to user-{user_id}: {e}")
        return False


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
        
        # Active games with optimized queries, ordered by most recent
        active_games = Game.objects.select_related(
            'black_player', 'white_player', 'ruleset'
        ).filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')
        
        # Recent finished games for left panel (limit to 5)
        recent_finished_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner', 'ruleset'
        ).filter(
            user_games_query, 
            status=GameStatus.FINISHED
        ).order_by('-finished_at')[:5]
        
        # Game selection logic for center panel
        selected_game = None
        game_id_param = self.request.GET.get('game')
        
        if game_id_param:
            # Try to select specific game from URL parameter
            try:
                selected_game = Game.objects.select_related(
                    'black_player', 'white_player', 'winner', 'ruleset'
                ).filter(
                    id=game_id_param
                ).filter(
                    Q(black_player=user) | Q(white_player=user)  # User must be a player
                ).first()
            except (Game.DoesNotExist, ValueError):
                # Invalid game ID or user not authorized - fall back to default
                pass
        
        # If no specific game selected, use most recent active game
        if not selected_game and active_games.exists():
            selected_game = active_games.first()
        
        # Friends for right panel
        from web.models import Friendship
        friends = Friendship.objects.get_friends(user)
        
        # Pending challenges with optimized queries
        
        # Challenges sent by the current user (pending)
        pending_sent_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        # Challenges received by the current user (pending)
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenged=user, 
            status=ChallengeStatus.PENDING
        )
        
        context.update({
            'games_played': games_played,
            'games_won': games_won,
            'active_games': active_games,
            'recent_finished_games': recent_finished_games,
            'selected_game': selected_game,  # New: Selected game for center panel
            'friends': friends,
            'pending_sent_challenges': pending_sent_challenges,
            'pending_received_challenges': pending_received_challenges,
            # Keep legacy key for backward compatibility
            'pending_challenges': pending_received_challenges,
        })
        return context
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests, return partial for HTMX or full page."""
        # If HTMX request with game parameter, return just the game panel
        if request.headers.get('HX-Request') and request.GET.get('game'):
            context = self.get_context_data(**kwargs)
            return render(request, 'web/partials/dashboard_game_panel.html', context)
        
        # Otherwise return full dashboard
        return super().get(request, *args, **kwargs)


class GamesView(LoginRequiredMixin, UserGamesMixin, TemplateView):
    """List user's games."""
    template_name = 'web/games.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Use mixin and optimize queries
        user_games_query = self.get_user_games_query(user)
        from django.db.models import Case, When, Value, IntegerField
        
        user_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner', 'ruleset'
        ).filter(user_games_query).order_by(
            # Active games first, then by most recent
            Case(
                When(status=GameStatus.ACTIVE, then=Value(0)),
                When(status=GameStatus.WAITING, then=Value(1)),
                When(status=GameStatus.FINISHED, then=Value(2)),
                When(status=GameStatus.ABANDONED, then=Value(3)),
                output_field=IntegerField(),
            ),
            '-created_at'
        )
        
        context['games'] = user_games
        return context


class GameDetailRedirectView(LoginRequiredMixin, RedirectView):
    """Redirect game detail requests to dashboard with game parameter."""
    login_url = 'web:login'
    permanent = False  # Use temporary redirect (302)
    
    def get_redirect_url(self, *args, **kwargs):
        from django.urls import reverse
        game_id = kwargs.get('game_id')
        if game_id:
            return f"{reverse('web:dashboard')}?game={game_id}"
        else:
            return reverse('web:dashboard')


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
                    # Both players need to receive the updated board state:
                    # - The player who moved needs to see they can't move anymore
                    # - The other player needs to see the move and that they can now move
                    players_to_notify = [game.black_player, game.white_player]
                    
                    logger.info(f"📡 SSE: Will notify both players about move in game {game.id}")
                    
                    try:
                        # Send HTML fragment for HTMX SSE to both players
                        from django.middleware.csrf import get_token
                        csrf_token = get_token(request)
                        logger.debug(f"🔐 CSRF: Token generated for SSE: {csrf_token[:10]}..." if csrf_token else "🔐 CSRF: No token generated")
                        
                        # Use Django template and prevent all escaping
                        from django.template.loader import render_to_string
                        import json
                        
                        # Send to both players with their respective contexts
                        for notify_user in players_to_notify:
                            notify_user_id = notify_user.id
                            notify_username = notify_user.username
                            
                            try:
                                # Always use dashboard context since standalone game page is removed
                                board_html = render_to_string('web/partials/game_board.html', {
                                    'game': game,
                                    'user': notify_user,  # Each player gets their own context
                                    'csrf_token': csrf_token,
                                    'wrapper_id': 'dashboard-game-board-content'  # Always use dashboard wrapper
                                }, request=request).strip()
                                
                                # Fix SSE protocol newline issues while preserving HTML structure
                                board_html_sse = board_html.replace('\n\n', ' ').replace('\r\n\r\n', ' ').strip()
                                
                                # Log details for this player
                                clickable_count = board_html.count('hx-post')
                                is_current_player = (notify_user == game.get_current_player_user())
                                logger.debug(f"📄 {notify_username}: Board HTML ({len(board_html)} chars), {clickable_count} clickable, current_player={is_current_player}")
                                
                                channel = f'user-{notify_user_id}'
                                event_name = 'game_move'
                                
                                # Send the newline-stripped HTML content for HTMX to process
                                # Try WebSocket first, fall back to SSE
                                try:
                                    from .consumers import WebSocketMessageSender
                                    WebSocketMessageSender.send_to_user_sync(
                                        notify_user_id, 
                                        event_name, 
                                        board_html_sse,
                                        metadata={'game_id': str(game.id), 'target_user': notify_username}
                                    )
                                    logger.info(f"📤 WebSocket: Event '{event_name}' sent to {notify_username}")
                                except Exception as ws_error:
                                    logger.warning(f"WebSocket failed, falling back to SSE: {ws_error}")
                                    send_event(channel, event_name, board_html_sse, json_encode=False)
                                    logger.info(f"📤 SSE: Event '{event_name}' sent to {notify_username} (fallback)")
                                
                                # Also send dashboard panel updates for this player
                                try:
                                    # Generate updated games panel for dashboard
                                    from django.db.models import Q
                                    user_games_query = Q(black_player=notify_user) | Q(white_player=notify_user)
                                    
                                    # Get updated active games and recent finished games
                                    active_games = Game.objects.select_related(
                                        'black_player', 'white_player', 'ruleset'
                                    ).filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')
                                    
                                    recent_finished_games = Game.objects.select_related(
                                        'black_player', 'white_player', 'winner', 'ruleset'
                                    ).filter(
                                        user_games_query, 
                                        status=GameStatus.FINISHED
                                    ).order_by('-finished_at')[:5]
                                    
                                    # Don't force game selection - preserve user's current view
                                    # The games panel will update turn indicators without changing selection
                                    selected_game_for_panel = None
                                    
                                    # Render updated games panel
                                    panel_html = render_to_string('web/partials/games_panel.html', {
                                        'user': notify_user,
                                        'active_games': active_games,
                                        'recent_finished_games': recent_finished_games,
                                        'selected_game': selected_game_for_panel
                                    }, request=request).strip()
                                    
                                    # Send dashboard panel update
                                    panel_html_sse = panel_html.replace('\n\n', ' ').replace('\r\n\r\n', ' ').strip()
                                    # Try WebSocket first, fall back to SSE
                                    try:
                                        WebSocketMessageSender.send_to_user_sync(
                                            notify_user_id,
                                            'dashboard_update',
                                            panel_html_sse,
                                            metadata={'game_id': str(game.id), 'panel_type': 'games_list'}
                                        )
                                        logger.info(f"📤 WebSocket: Dashboard panel update sent to {notify_username}")
                                    except Exception as ws_error:
                                        logger.warning(f"Dashboard WebSocket failed, falling back to SSE: {ws_error}")
                                        send_event(channel, 'dashboard_update', panel_html_sse, json_encode=False)
                                        logger.info(f"📊 SSE: Dashboard panel update sent to {notify_username} (fallback)")
                                    
                                    # REMOVED: Dashboard embedded game panel update
                                    # This was causing forced view switching when other players made moves
                                    # Users should maintain their current game view context
                                    
                                except Exception as panel_error:
                                    logger.warning(f"⚠️  SSE: Dashboard panel update failed for {notify_username}: {panel_error}")
                                
                            except Exception as e:
                                # Don't fail the request if SSE fails for this player
                                logger.error(f"❌ SSE: Failed to send event to {notify_username}: {type(e).__name__}: {str(e)}")
                                import traceback
                                logger.debug(f"📋 SSE: Full traceback for {notify_username}: {traceback.format_exc()}")
                        
                    except Exception as e:
                        # Overall SSE failure
                        logger.error(f"❌ SSE: Overall SSE processing failed: {type(e).__name__}: {str(e)}")
                        import traceback
                        logger.debug(f"📋 SSE: Overall traceback: {traceback.format_exc()}")
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
    
    def handle_error_response(self, request, message, status=400):
        """Handle error response for both HTMX and JSON requests."""
        if request.headers.get('HX-Request'):
            return render(request, 'web/partials/friend_request_result.html', {
                'error': message
            }, status=status)
        return self.json_error(message, status)

    def post(self, request):
        username = request.POST.get('username')
        if not username:
            return self.handle_error_response(request, 'Username is required', 400)
        
        # Check if trying to befriend self
        if username == request.user.username:
            return self.handle_error_response(request, 'Cannot send friend request to yourself', 400)
        
        # Check if user exists
        addressee = self.get_user_or_404(username)
        if not addressee:
            return self.handle_error_response(request, 'User not found', 404)
        
        # Check if friendship already exists
        existing = Friendship.objects.filter(
            Q(requester=request.user, addressee=addressee) |
            Q(requester=addressee, addressee=request.user)
        ).first()
        
        if existing:
            return self.handle_error_response(request, 'Friend request already exists', 400)
        
        # Create friendship
        try:
            friendship = Friendship.objects.create(
                requester=request.user,
                addressee=addressee
            )
            
            # Handle HTMX requests
            if request.headers.get('HX-Request'):
                return render(request, 'web/partials/friend_request_result.html', {
                    'success': True,
                    'message': f'Friend request sent to {username}!',
                    'username': username
                })
            
            # Handle JSON API requests
            return self.json_response({
                'message': 'Friend request sent',
                'friendship_id': friendship.id
            }, 201)
        except ValidationError as e:
            return self.handle_error_response(request, str(e), 400)


class RespondFriendRequestView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Respond to a friend request (accept/reject)."""
    login_url = 'web:login'
    
    def handle_error_response(self, request, message, status=400):
        """Handle error response for both HTMX and JSON requests."""
        if request.headers.get('HX-Request'):
            return render(request, 'web/partials/friend_request_error.html', {
                'error': message
            }, status=status)
        return self.json_error(message, status)
    
    def post(self, request, friendship_id):
        action = request.POST.get('action')
        if action not in ['accept', 'reject']:
            return self.handle_error_response(request, 'Invalid action', 400)
        
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            return self.handle_error_response(request, 'Friend request not found', 404)
        
        # Check if user is the addressee
        if friendship.addressee != request.user:
            return self.handle_error_response(request, 'Access denied', 403)
        
        # Check if status is pending
        if friendship.status != FriendshipStatus.PENDING:
            return self.handle_error_response(request, 'Friend request is no longer pending', 400)
        
        # Update status
        if action == 'accept':
            friendship.status = FriendshipStatus.ACCEPTED
        else:
            friendship.status = FriendshipStatus.REJECTED
        
        friendship.save()
        
        # Handle HTMX requests - return updated pending requests section
        if request.headers.get('HX-Request'):
            # Get updated pending requests for current user
            pending_requests = Friendship.objects.get_pending_requests(request.user)
            return render(request, 'web/partials/pending_requests.html', {
                'pending_requests': pending_requests
            })
        
        # Handle JSON API requests
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
            if request.headers.get('HX-Request'):
                return render(request, 'web/partials/search_results.html', {'users': []})
            return self.json_response([])
        
        # Search users by username (excluding self)
        users = User.objects.filter(
            username__icontains=query
        ).exclude(id=request.user.id)[:10]
        
        # Return HTMX template for HTMX requests
        if request.headers.get('HX-Request'):
            return render(request, 'web/partials/search_results.html', {'users': users})
        
        # Return JSON for API requests
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
    
    def get_friends(self, user):
        """Get user's friends list."""
        return Friendship.objects.get_friends(user)
    
    def _get_updated_friends_context(self, user):
        """Get updated context for friends panel."""
        # Get friends
        friends = Friendship.objects.get_friends(user)
        
        # Get pending challenges
        pending_sent_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenged=user, 
            status=ChallengeStatus.PENDING
        )
        
        return {
            'friends': friends,
            'pending_sent_challenges': pending_sent_challenges,
            'pending_received_challenges': pending_received_challenges,
            'user': user,
        }
    
    def handle_error_response(self, request, message, status=400):
        """Handle error response for both HTMX and JSON requests."""
        if request.headers.get('HX-Request'):
            return render(request, 'web/partials/challenge_error.html', {
                'error': message
            }, status=status)
        return self.json_error(message, status)
    
    def get(self, request):
        """Return challenge modal content for HTMX."""
        username = request.GET.get('username', '')
        
        # Get available rulesets
        rulesets = RuleSet.objects.all().order_by('board_size', 'name')
        
        return render(request, 'web/partials/challenge_modal.html', {
            'username': username,
            'rulesets': rulesets
        })
    
    def post(self, request):
        username = request.POST.get('username')
        ruleset_id = request.POST.get('ruleset_id')
        
        # Debug logging to see what's being sent
        from loguru import logger
        logger.info(f"🎯 Challenge POST: username='{username}', ruleset_id='{ruleset_id}'")
        logger.info(f"📋 Full POST data: {dict(request.POST)}")
        logger.info(f"🔍 POST keys: {list(request.POST.keys())}")
        
        if not username or not ruleset_id:
            logger.warning(f"❌ Missing data: username='{username}', ruleset_id='{ruleset_id}'")
            return self.handle_error_response(request, 'Username and ruleset are required', 400)
        
        logger.info(f"✅ Initial validation passed")
        
        # Check if trying to challenge self
        if username == request.user.username:
            logger.warning(f"❌ User trying to challenge self: {username}")
            return self.handle_error_response(request, 'Cannot challenge yourself', 400)
        
        logger.info(f"✅ Self-challenge check passed")
        
        # Check if user exists
        challenged_user = self.get_user_or_404(username)
        if not challenged_user:
            logger.warning(f"❌ User not found: {username}")
            return self.handle_error_response(request, 'User not found', 404)
        
        logger.info(f"✅ User exists: {challenged_user.username}")
        
        # Check if they are friends
        is_friend = Friendship.objects.filter(
            Q(requester=request.user, addressee=challenged_user, status=FriendshipStatus.ACCEPTED) |
            Q(requester=challenged_user, addressee=request.user, status=FriendshipStatus.ACCEPTED)
        ).exists()
        
        if not is_friend:
            logger.warning(f"❌ Users are not friends: {request.user.username} -> {username}")
            return self.handle_error_response(request, 'You can only challenge friends', 400)
        
        logger.info(f"✅ Friendship check passed")
        
        # Check if ruleset exists
        try:
            ruleset = RuleSet.objects.get(id=ruleset_id)
            logger.info(f"✅ Ruleset found: {ruleset.name} (ID: {ruleset.id})")
        except RuleSet.DoesNotExist:
            logger.warning(f"❌ Invalid ruleset ID: {ruleset_id}")
            return self.handle_error_response(request, 'Invalid ruleset', 400)
        
        # Check for existing pending challenge
        existing = Challenge.objects.filter(
            challenger=request.user,
            challenged=challenged_user,
            status=ChallengeStatus.PENDING
        ).first()
        
        if existing:
            logger.warning(f"❌ Existing pending challenge found: {existing.id}")
            return self.handle_error_response(request, 'You already have a pending challenge with this user', 400)
        
        logger.info(f"✅ No existing challenge check passed")
        
        # Create challenge
        try:
            logger.info(f"🎯 Creating challenge: {request.user.username} -> {challenged_user.username}")
            
            challenge = Challenge.objects.create(
                challenger=request.user,
                challenged=challenged_user,
                ruleset=ruleset
            )
            
            logger.info(f"✅ Challenge created successfully: {challenge.id}")
            
            # Send real-time update to challenged user
            try:
                from .consumers import WebSocketMessageSender
                from django.template.loader import render_to_string
                
                # Get updated friends context for the challenged user
                challenged_user_context = self._get_updated_friends_context(challenged_user)
                challenged_user_context['csrf_token'] = request.META.get('CSRF_COOKIE')
                
                # Render updated friends panel for challenged user
                friends_panel_html = render_to_string('web/partials/friends_panel.html', 
                    challenged_user_context, request=request).strip()
                
                # Send WebSocket update to challenged user
                WebSocketMessageSender.send_to_user_sync(
                    challenged_user.id,
                    'friends_update',
                    friends_panel_html,
                    metadata={'challenge_id': str(challenge.id), 'action': 'challenge_received'}
                )
                logger.info(f"📤 WebSocket: Challenge notification sent to {challenged_user.username}")
                
            except Exception as ws_error:
                logger.warning(f"⚠️  WebSocket challenge notification failed: {ws_error}")
                # Don't fail the request if WebSocket fails
            
            # Handle HTMX requests
            if request.headers.get('HX-Request'):
                logger.info(f"📤 Returning HTMX response")
                return render(request, 'web/partials/challenge_success.html', {
                    'success': True,
                    'message': f'Challenge sent to {username}!',
                    'challenged_user': username,
                    'ruleset': ruleset
                })
            
            # Handle regular requests (JSON API)
            logger.info(f"📤 Returning JSON response")
            return self.json_response({
                'success': True,
                'message': f'Challenge sent to {username}',
                'challenge_id': str(challenge.id)
            }, 200)
            
        except Exception as e:
            logger.error(f"❌ Exception during challenge creation: {type(e).__name__}: {str(e)}")
            # Handle HTMX error responses
            if request.headers.get('HX-Request'):
                return render(request, 'web/partials/challenge_error.html', {
                    'error': f'Failed to create challenge: {str(e)}'
                }, status=500)
            
            return self.json_error(f'Failed to create challenge: {str(e)}', 500)


class RespondChallengeView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Respond to a game challenge (accept/reject)."""
    login_url = 'web:login'
    
    def _get_updated_friends_context(self, user):
        """Get updated context for friends panel."""
        # Get friends
        friends = Friendship.objects.get_friends(user)
        
        # Get pending challenges
        pending_sent_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenged=user, 
            status=ChallengeStatus.PENDING
        )
        
        return {
            'friends': friends,
            'pending_sent_challenges': pending_sent_challenges,
            'pending_received_challenges': pending_received_challenges,
            'user': user,
        }
    
    def post(self, request, challenge_id):
        action = request.POST.get('action')
        if action not in ['accept', 'reject', 'cancel']:
            return self.json_error('Invalid action', 400)
        
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            return self.json_error('Challenge not found', 404)
        
        # Check user permissions based on action
        if action == 'cancel':
            # Only the challenger can cancel their own challenge
            if challenge.challenger != request.user:
                return self.json_error('Access denied - only challenger can cancel', 403)
        else:
            # Only the challenged party can accept/reject
            if challenge.challenged != request.user:
                return self.json_error('Access denied - only challenged party can accept/reject', 403)
        
        # Check if challenge is still pending
        if challenge.status != ChallengeStatus.PENDING:
            return self.json_error('Challenge is no longer pending', 400)
        
        # Challenges no longer expire - removed expiration check
        
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
                
                # For HTMX requests, return updated friends panel and redirect to game
                if request.headers.get('HX-Request'):
                    # First update the friends panel to remove the challenge
                    context = self._get_updated_friends_context(request.user)
                    response = render(request, 'web/partials/friends_panel.html', context)
                    # Then redirect to the new game
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
        
        elif action == 'reject':
            challenge.status = ChallengeStatus.REJECTED
            challenge.save()
            
            # For HTMX requests, return updated friends panel
            if request.headers.get('HX-Request'):
                context = self._get_updated_friends_context(request.user)
                return render(request, 'web/partials/friends_panel.html', context)
            
            return self.json_response({
                'success': True,
                'message': 'Challenge rejected'
            })
        
        elif action == 'cancel':
            challenge.status = ChallengeStatus.CANCELLED
            challenge.save()
            
            # For HTMX requests, return updated friends panel
            if request.headers.get('HX-Request'):
                context = self._get_updated_friends_context(request.user)
                return render(request, 'web/partials/friends_panel.html', context)
            
            return self.json_response({
                'success': True,
                'message': 'Challenge cancelled'
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
