"""
URL configuration for gomoku project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from users.views import UserViewSet
from games.views import (
    RuleSetViewSet, GameViewSet, PlayerSessionViewSet, ChallengeViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'rulesets', RuleSetViewSet)
router.register(r'games', GameViewSet)
router.register(r'sessions', PlayerSessionViewSet)
router.register(r'challenges', ChallengeViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/token/', obtain_auth_token, name='api_token_auth'),
    path('api/v1/events/', include('django_eventstream.urls'), {'channels': ['user-{user_id}']}),
    path('api-auth/', include('rest_framework.urls')),
    path('', include('web.urls')),  # Root goes to web interface
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
