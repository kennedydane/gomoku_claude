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
    path('login/', views.WebLoginView.as_view(), name='login'),
    path('logout/', views.WebLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Dashboard and profile
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Games
    path('games/', views.GamesView.as_view(), name='games'),
    path('games/<uuid:game_id>/', views.GameDetailView.as_view(), name='game_detail'),
    path('games/<uuid:game_id>/move/', views.GameMoveView.as_view(), name='game_move'),
    
    # Friends - Web Pages
    path('friends/', views.FriendsPageView.as_view(), name='friends'),
    path('friends', RedirectView.as_view(pattern_name='web:friends', permanent=True)),
    
    # Friends - API Endpoints
    path('api/send-friend-request/', views.SendFriendRequestView.as_view(), name='send_friend_request'),
    path('api/respond-friend-request/<int:friendship_id>/', views.RespondFriendRequestView.as_view(), name='respond_friend_request'),
    path('api/friends-list/', views.FriendsListView.as_view(), name='friends_list'),
    path('api/pending-requests/', views.PendingRequestsView.as_view(), name='pending_requests'),
    path('api/search-users/', views.SearchUsersView.as_view(), name='search_users'),
]