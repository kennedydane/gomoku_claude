"""
URL configuration for web interface.
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'web'

urlpatterns = [
    # Root and authentication
    path('', views.RootRedirectView.as_view(), name='root'),
    path('login/', views.WebLoginView.as_view(), name='login'),
    path('logout/', views.WebLogoutView.as_view(), name='logout'),
    
    # Dashboard and profile
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Games
    path('games/modal/', views.GamesModalView.as_view(), name='games_modal'),
    path('games/<uuid:game_id>/', views.GameDetailRedirectView.as_view(), name='game_detail'),
    path('games/<uuid:game_id>/move/', views.GameMoveView.as_view(), name='game_move'),
    path('games/<uuid:game_id>/resign/', views.GameResignView.as_view(), name='game_resign'),
    
    # Friends - Modal View
    path('friends/modal/', views.FriendsModalView.as_view(), name='friends_modal'),
    
    # Friends - API Endpoints
    path('api/send-friend-request/', views.SendFriendRequestView.as_view(), name='send_friend_request'),
    path('api/respond-friend-request/<int:friendship_id>/', views.RespondFriendRequestView.as_view(), name='respond_friend_request'),
    path('api/pending-requests/', views.PendingRequestsView.as_view(), name='pending_requests'),
    path('api/search-users/', views.SearchUsersView.as_view(), name='search_users'),
    path('api/blocked-users/', views.BlockedUsersView.as_view(), name='blocked_users'),
    path('api/unblock-user/<int:friendship_id>/', views.UnblockUserView.as_view(), name='unblock_user'),
    
    # Challenge - API Endpoints
    path('api/challenge-friend/', views.ChallengeFriendView.as_view(), name='challenge_friend'),
    path('api/respond-challenge/<uuid:challenge_id>/', views.RespondChallengeView.as_view(), name='respond_challenge'),
    path('api/rulesets/', views.RulesetsListView.as_view(), name='rulesets_list'),
]