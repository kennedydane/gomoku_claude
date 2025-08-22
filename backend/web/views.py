from typing import Optional, Union, Dict, Any
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.urls import reverse_lazy, reverse
from django.views import View
from django.db.models import Q
from django.http import JsonResponse, HttpResponse

from games.models import Game, Challenge, GameStatus, ChallengeStatus, GomokuRuleSet, GoRuleSet
from games.game_services import GameServiceFactory
from core.exceptions import InvalidMoveError, GameStateError, PlayerError
from users.models import User
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


class RootRedirectView(RedirectView):
    """Smart root redirect: dashboard for authenticated users, login for anonymous."""
    permanent = False  # Use temporary redirect (302)
    
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse('web:dashboard')
        else:
            return reverse('web:login')


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
        return redirect('web:root')
    
    def post(self, request):
        """Handle POST logout."""
        if request.user.is_authenticated:
            from django.contrib.auth import logout
            logout(request)
        return redirect('web:root')




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
            'black_player', 'white_player'
        ).prefetch_related('ruleset').filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')
        
        # Recent finished games for left panel (limit to 5)
        recent_finished_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner'
        ).prefetch_related('ruleset').filter(
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
                    'black_player', 'white_player', 'winner'
                ).prefetch_related('ruleset').filter(
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
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        # Challenges received by the current user (pending)
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
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
                'black_player', 'white_player'
            ).prefetch_related('ruleset').get(id=game_id)
            
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
            
            # Make the move using game-specific service
            try:
                service = game.get_service()
                move = service.make_move(game, request.user.id, row, col)
                
                # Refresh game from database to get updated state
                game.refresh_from_db()
                
                # Send real-time notifications to both players
                logger.info(f"🎮 MOVE: Processing move by {request.user.username} in game {game.id}")
                
                # Use centralized WebSocket notification service
                try:
                    from .services import WebSocketNotificationService
                    
                    success = WebSocketNotificationService.notify_game_event(
                        event_type='game_move_made',
                        game=game,
                        triggering_user=request.user,
                        request=request
                    )
                    
                    if not success:
                        logger.warning(f"Some WebSocket notifications failed for move in game {game.id}")
                        
                except Exception as e:
                    logger.error(f"WebSocket notification failed for move: {e}")
                    # Don't let WebSocket errors break the move response
                
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
    


class SendFriendRequestView(LoginRequiredMixin, View):
    """Send a friend request to another user."""
    login_url = 'web:login'
    
    def get_user_or_404(self, username):
        """Get user by username or return None."""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def post(self, request):
        username = request.POST.get('username')
        if not username:
            return render(request, 'web/partials/friend_request_result.html', {
                'error': 'Username is required'
            }, status=400)
        
        # Check if trying to befriend self
        if username == request.user.username:
            return render(request, 'web/partials/friend_request_result.html', {
                'error': 'Cannot send friend request to yourself'
            }, status=400)
        
        # Check if user exists
        addressee = self.get_user_or_404(username)
        if not addressee:
            return render(request, 'web/partials/friend_request_result.html', {
                'error': 'User not found'
            }, status=404)
        
        # Check if blocked
        if Friendship.objects.is_blocked(request.user, addressee):
            return render(request, 'web/partials/friend_request_result.html', {
                'error': 'You have been blocked by this user'
            }, status=403)
        
        # Check if can send request (handles existing friendship and pending requests)
        if not Friendship.objects.can_send_request(request.user, addressee):
            return render(request, 'web/partials/friend_request_result.html', {
                'error': 'Cannot send friend request at this time'
            }, status=400)
        
        # Create friendship
        try:
            friendship = Friendship.objects.create(
                requester=request.user,
                addressee=addressee
            )
            
            return render(request, 'web/partials/friend_request_result.html', {
                'success': True,
                'message': f'Friend request sent to {username}!',
                'username': username
            })
            
        except ValidationError as e:
            return render(request, 'web/partials/friend_request_result.html', {
                'error': str(e)
            }, status=400)


class RespondFriendRequestView(LoginRequiredMixin, View):
    """Respond to a friend request (accept/reject/block)."""
    login_url = 'web:login'
    
    def post(self, request, friendship_id):
        action = request.POST.get('action')
        if action not in ['accept', 'reject', 'block']:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Invalid action'
            }, status=400)
        
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Friend request not found'
            }, status=404)
        
        # Check if user is the addressee
        if friendship.addressee != request.user:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Access denied'
            }, status=403)
        
        # Check if status is pending
        if friendship.status != FriendshipStatus.PENDING:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Friend request is no longer pending'
            }, status=400)
        
        # Update status
        if action == 'accept':
            friendship.status = FriendshipStatus.ACCEPTED
        elif action == 'reject':
            friendship.status = FriendshipStatus.REJECTED
        elif action == 'block':
            friendship.status = FriendshipStatus.BLOCKED
        
        friendship.save()
        
        # Return updated pending requests section
        pending_requests = Friendship.objects.get_pending_requests(request.user)
        return render(request, 'web/partials/pending_requests.html', {
            'pending_requests': pending_requests
        })



class PendingRequestsView(LoginRequiredMixin, View):
    """Get user's pending friend requests as HTML for modal."""
    login_url = 'web:login'
    
    def get(self, request):
        pending_requests = Friendship.objects.get_pending_requests(request.user)
        return render(request, 'web/partials/pending_requests.html', {
            'pending_requests': pending_requests
        })


class SearchUsersView(LoginRequiredMixin, View):
    """Search for users to befriend."""
    login_url = 'web:login'
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return render(request, 'web/partials/search_results.html', {'users': []})
        
        # Search users by username (excluding self)
        users = User.objects.filter(
            username__icontains=query
        ).exclude(id=request.user.id)[:10]
        
        return render(request, 'web/partials/search_results.html', {'users': users})
    
    def post(self, request):
        # Handle search form submission (same as GET)
        return self.get(request)




class FriendsModalView(LoginRequiredMixin, TemplateView):
    """Modal content for friends management."""
    template_name = 'web/partials/friends_modal_content.html'
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


class GamesModalView(LoginRequiredMixin, TemplateView):
    """Modal content for games management and viewing."""
    template_name = 'web/partials/games_modal_content.html'
    login_url = 'web:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's games with same logic as GamesView
        from django.db.models import Q
        user_games_query = Q(black_player=user) | Q(white_player=user)
        
        # Get all games for this user
        all_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner'
        ).prefetch_related('ruleset').filter(user_games_query).order_by('-created_at')
        
        # Separate active and finished games
        active_games = all_games.filter(status=GameStatus.ACTIVE)
        finished_games = all_games.filter(status=GameStatus.FINISHED)
        
        context.update({
            'active_games': active_games,
            'finished_games': finished_games,
            'total_games': all_games.count(),
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
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
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
        
        # Get available rulesets (combine Gomoku and Go rulesets)
        gomoku_rulesets = list(GomokuRuleSet.objects.all())
        go_rulesets = list(GoRuleSet.objects.all())
        rulesets = sorted(gomoku_rulesets + go_rulesets, key=lambda r: (r.board_size, r.name))
        
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
        
        # Parse ruleset_id which now includes game type prefix (e.g., "gomoku_3" or "go_3")
        try:
            if '_' not in ruleset_id:
                logger.warning(f"❌ Invalid ruleset format: {ruleset_id}")
                return self.handle_error_response(request, 'Invalid ruleset format', 400)
            
            game_type_str, actual_id = ruleset_id.split('_', 1)
            actual_id = int(actual_id)
            
            logger.info(f"🎯 Parsed ruleset: type='{game_type_str}', id={actual_id}")
            
            # Get the appropriate ruleset based on the game type
            ruleset = None
            if game_type_str == 'gomoku':
                ruleset = GomokuRuleSet.objects.get(id=actual_id)
                logger.info(f"✅ Gomoku Ruleset found: {ruleset.name} (ID: {ruleset.id})")
            elif game_type_str == 'go':
                ruleset = GoRuleSet.objects.get(id=actual_id)
                logger.info(f"✅ Go Ruleset found: {ruleset.name} (ID: {ruleset.id})")
            else:
                logger.warning(f"❌ Unknown game type: {game_type_str}")
                return self.handle_error_response(request, f'Unknown game type: {game_type_str}', 400)
                
        except (ValueError, GomokuRuleSet.DoesNotExist, GoRuleSet.DoesNotExist) as e:
            logger.warning(f"❌ Ruleset lookup failed: {ruleset_id} - {e}")
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
            
            # Properly set Generic Foreign Key fields for the challenge
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(ruleset)
            
            challenge = Challenge.objects.create(
                challenger=request.user,
                challenged=challenged_user,
                ruleset_content_type=content_type,
                ruleset_object_id=ruleset.id
            )
            
            logger.info(f"✅ Challenge created successfully: {challenge.id}")
            logger.info(f"🎯 Challenge ruleset: {challenge.ruleset.name} ({challenge.ruleset.__class__.__name__})")
            
            # Send real-time updates to both users using centralized service
            try:
                from .services import WebSocketNotificationService
                
                # Create a temporary game object to pass the challenge relationships
                # The centralized service expects a game, but for challenges we need to pass challenge info
                WebSocketNotificationService.notify_game_event(
                    event_type='challenge_sent',
                    game=None,  # No game yet, just challenge
                    triggering_user=request.user,
                    request=request,
                    challenge=challenge,
                    metadata={'challenge_id': str(challenge.id)}
                )
                
                logger.info(f"📤 WebSocket: Challenge notifications sent via centralized service")
                
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
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
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
        # DEBUG: Log all request details
        from loguru import logger
        logger.info(f"🔍 CHALLENGE RESPONSE DEBUG: challenge_id={challenge_id}")
        logger.info(f"📋 Request method: {request.method}")
        logger.info(f"📋 Request path: {request.path}")
        logger.info(f"📋 POST data keys: {list(request.POST.keys())}")
        logger.info(f"📋 POST data values: {dict(request.POST)}")
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"📋 User: {request.user}")
        logger.info(f"📋 CSRF cookie: {request.META.get('CSRF_COOKIE')}")
        logger.info(f"📋 X-CSRFToken header: {request.headers.get('X-CSRFToken')}")
        logger.info(f"📋 csrfmiddlewaretoken in POST: {request.POST.get('csrfmiddlewaretoken')}")
        
        action = request.POST.get('action')
        logger.info(f"📋 Action: {action}")
        
        if action not in ['accept', 'reject', 'cancel']:
            logger.error(f"❌ Invalid action: {action}")
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
                
                # Properly set Generic Foreign Key fields for the game
                from django.contrib.contenttypes.models import ContentType
                challenge_ruleset = challenge.ruleset  # Get the ruleset object
                content_type = ContentType.objects.get_for_model(challenge_ruleset)
                
                game = Game.objects.create(
                    black_player=black_player,
                    white_player=white_player,
                    ruleset_content_type=content_type,
                    ruleset_object_id=challenge_ruleset.id,
                    status=GameStatus.ACTIVE
                )
                game.initialize_board()
                game.save()
                
                # Debug logging for game creation
                logger.info(f"✅ Game created successfully: {game.id}")
                logger.info(f"🎯 Game ruleset: {game.ruleset.name} ({game.ruleset.__class__.__name__})")
                logger.info(f"🎯 Game board size: {game.ruleset.board_size}x{game.ruleset.board_size}")
                logger.info(f"🎯 Game type: {game.ruleset.game_type}")
                
                # Send real-time updates to both users using centralized service
                try:
                    from .services import WebSocketNotificationService
                    
                    WebSocketNotificationService.notify_game_event(
                        event_type='challenge_accepted',
                        game=game,
                        triggering_user=request.user,
                        request=request,
                        challenge=challenge,
                        metadata={'challenge_id': str(challenge.id), 'game_id': str(game.id)}
                    )
                    
                    from loguru import logger
                    logger.info(f"📤 WebSocket: Game creation notifications sent via centralized service")
                    
                except Exception as ws_error:
                    from loguru import logger
                    logger.warning(f"⚠️ WebSocket game creation notification failed: {ws_error}")
                
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
            
            # Send real-time updates to both users using centralized service
            try:
                from .services import WebSocketNotificationService
                
                WebSocketNotificationService.notify_game_event(
                    event_type='challenge_rejected',
                    game=None,  # No game for rejected challenges
                    triggering_user=request.user,
                    request=request,
                    challenge=challenge,
                    metadata={'challenge_id': str(challenge.id), 'action': 'rejected'}
                )
                
                from loguru import logger
                logger.info(f"📤 WebSocket: Challenge rejection notifications sent via centralized service")
                
            except Exception as ws_error:
                from loguru import logger
                logger.warning(f"⚠️ WebSocket challenge rejection notification failed: {ws_error}")
            
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
            
            # Send real-time updates to both users using centralized service
            try:
                from .services import WebSocketNotificationService
                
                # For cancellations, we can reuse challenge_rejected event type
                WebSocketNotificationService.notify_game_event(
                    event_type='challenge_rejected',
                    game=None,  # No game for cancelled challenges
                    triggering_user=request.user,
                    request=request,
                    challenge=challenge,
                    metadata={'challenge_id': str(challenge.id), 'action': 'cancelled'}
                )
                
                from loguru import logger
                logger.info(f"📤 WebSocket: Challenge cancellation notifications sent via centralized service")
                
            except Exception as ws_error:
                from loguru import logger
                logger.warning(f"⚠️ WebSocket challenge cancellation notification failed: {ws_error}")
            
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
        # Get available rulesets (combine Gomoku and Go rulesets)
        gomoku_rulesets = list(GomokuRuleSet.objects.all())
        go_rulesets = list(GoRuleSet.objects.all())
        rulesets = sorted(gomoku_rulesets + go_rulesets, key=lambda r: (r.board_size, r.name))
        
        rulesets_data = [{
            'id': ruleset.id,
            'name': ruleset.name,
            'description': ruleset.description,
            'board_size': ruleset.board_size,
            'allow_overlines': ruleset.allow_overlines
        } for ruleset in rulesets]
        
        return self.json_response(rulesets_data)


class GameResignView(FriendAPIViewMixin, LoginRequiredMixin, View):
    """Handle game resignation through web interface."""
    login_url = 'web:login'
    
    def post(self, request, game_id):
        """Resign from a game."""
        try:
            from games.models import Game
            from games.game_services import GameServiceFactory
            from games.models import GameEvent
            from games.serializers import GameSerializer
            
            # Get the game
            try:
                game = Game.objects.get(id=game_id)
            except Game.DoesNotExist:
                if request.headers.get('HX-Request'):
                    return render(request, 'web/partials/error_message.html', {
                        'error': 'Game not found'
                    }, status=404)
                return self.json_error('Game not found', 404)
            
            # Check if authenticated user is a player in this game
            user = request.user
            if user.id not in [game.black_player_id, game.white_player_id]:
                if request.headers.get('HX-Request'):
                    return render(request, 'web/partials/error_message.html', {
                        'error': 'You are not a player in this game'
                    }, status=403)
                return self.json_error('You are not a player in this game', 403)
            
            # Resign the game using game-specific service
            try:
                service = game.get_service()
                service.resign_game(game, user.id)
                
                # Create game event
                for player in [game.black_player, game.white_player]:
                    GameEvent.objects.create(
                        user=player,
                        event_type='resign',
                        event_data={
                            'game_id': str(game.id),
                            'resigned_player_id': user.id,
                            'winner_id': game.winner_id
                        }
                    )
                
                # Send real-time updates to both players using centralized service
                try:
                    from .services import WebSocketNotificationService
                    
                    WebSocketNotificationService.notify_game_event(
                        event_type='game_resigned',
                        game=game,
                        triggering_user=user,
                        request=request,
                        metadata={'resigned_by': user.id}
                    )
                    
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"📤 WebSocket: Game resignation notifications sent via centralized service")
                    
                except Exception as ws_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"⚠️ WebSocket resignation notification failed: {ws_error}")
                
                # For HTMX requests, return minimal response since WebSocket handles updates
                if request.headers.get('HX-Request'):
                    return HttpResponse(status=204)  # No Content - WebSocket will handle updates
                
                # For non-HTMX requests, return JSON
                return self.json_response({
                    'success': True,
                    'message': 'Game resigned successfully',
                    'game': GameSerializer(game).data
                })
                
            except Exception as e:
                if request.headers.get('HX-Request'):
                    return render(request, 'web/partials/error_message.html', {
                        'error': f'Failed to resign game: {str(e)}'
                    }, status=500)
                return self.json_error(f'Failed to resign game: {str(e)}', 500)
                
        except Exception as e:
            if request.headers.get('HX-Request'):
                return render(request, 'web/partials/error_message.html', {
                    'error': f'An error occurred: {str(e)}'
                }, status=500)
            return self.json_error(f'An error occurred: {str(e)}', 500)


class BlockedUsersView(LoginRequiredMixin, View):
    """Get user's blocked users list as HTML for modal."""
    login_url = 'web:login'
    
    def get(self, request):
        blocked_users = Friendship.objects.get_blocked_users(request.user)
        return render(request, 'web/partials/blocked_users.html', {
            'blocked_users': blocked_users
        })


class UnblockUserView(LoginRequiredMixin, View):
    """Unblock a user."""
    login_url = 'web:login'
    
    def post(self, request, friendship_id):
        try:
            friendship = Friendship.objects.get(id=friendship_id)
        except Friendship.DoesNotExist:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Blocked relationship not found'
            }, status=404)
        
        # Check if user is the addressee (the one who blocked)
        if friendship.addressee != request.user:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'Access denied'
            }, status=403)
        
        # Check if status is blocked
        if friendship.status != FriendshipStatus.BLOCKED:
            return render(request, 'web/partials/friend_request_error.html', {
                'error': 'User is not blocked'
            }, status=400)
        
        # Remove the blocked relationship completely
        friendship.delete()
        
        # Return updated blocked users section
        blocked_users = Friendship.objects.get_blocked_users(request.user)
        return render(request, 'web/partials/blocked_users.html', {
            'blocked_users': blocked_users
        })
