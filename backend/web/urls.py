"""
URL configuration for web interface.
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'web'

urlpatterns = [
    # Home and authentication
    path('', RedirectView.as_view(pattern_name='web:home'), name='root'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Dashboard and profile
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Games
    path('games/', views.GameListView.as_view(), name='games'),
    path('games/create/', views.GameCreateView.as_view(), name='create_game'),
    path('games/<uuid:game_id>/', views.GameDetailView.as_view(), name='game_detail'),
    path('games/<uuid:game_id>/move/', views.GameMoveView.as_view(), name='game_move'),
    path('games/<uuid:game_id>/resign/', views.GameResignView.as_view(), name='game_resign'),
    path('games/<uuid:game_id>/board/', views.GameBoardPartial.as_view(), name='game_board_partial'),
    
    # Friends
    path('friends/', views.FriendListView.as_view(), name='friends'),
    path('friends/search/', views.FriendSearchView.as_view(), name='friend_search'),
    path('friends/request/', views.FriendRequestView.as_view(), name='friend_request'),
    path('friends/respond/<int:request_id>/', views.FriendResponseView.as_view(), name='friend_response'),
    
    # Challenges
    path('challenges/', views.ChallengeListView.as_view(), name='challenges'),
    path('challenges/create/', views.ChallengeCreateView.as_view(), name='create_challenge'),
    path('challenges/respond/<uuid:challenge_id>/', views.ChallengeResponseView.as_view(), name='challenge_response'),
    
    # HTMX partials for dynamic updates
    path('partials/game-info/<uuid:game_id>/', views.GameInfoPartial.as_view(), name='game_info_partial'),
    path('partials/challenge-list/', views.ChallengeListPartial.as_view(), name='challenge_list_partial'),
    path('partials/friend-list/', views.FriendListPartial.as_view(), name='friend_list_partial'),
    path('partials/dashboard-stats/', views.DashboardStatsPartial.as_view(), name='dashboard_stats_partial'),
]