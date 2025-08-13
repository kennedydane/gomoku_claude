"""
DRF viewsets for user management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserStatsSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User CRUD operations.
    """
    queryset = User.objects.filter(is_active=True).prefetch_related(
        'games_as_black', 'games_as_white', 'moves'
    )
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'stats':
            return UserStatsSerializer
        return UserSerializer
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get user statistics."""
        user = self.get_object()
        serializer = UserStatsSerializer(user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reset_stats(self, request, pk=None):
        """Reset user statistics."""
        user = self.get_object()
        user.reset_stats()
        return Response({'message': 'Stats reset successfully'})
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete user by setting is_active to False."""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)