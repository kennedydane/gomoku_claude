"""
DRF viewsets for user management and enhanced authentication views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .models import User, EnhancedToken
from .serializers import UserSerializer, UserCreateSerializer, UserStatsSerializer
from .authentication import EnhancedTokenAuthentication


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User CRUD operations.
    """
    queryset = User.objects.filter(is_active=True).prefetch_related(
        'games_as_black', 'games_as_white', 'moves'
    )
    
    def get_permissions(self):
        """Allow unauthenticated user creation (registration)."""
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
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


@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def obtain_enhanced_token(request):
    """
    Obtain an enhanced authentication token.
    
    Accepts username, password, and optional device information.
    Returns an enhanced token with expiration and device tracking.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    device_name = request.data.get('device_name', '')
    device_info = request.data.get('device_info', {})
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create enhanced token
    token = EnhancedToken.objects.create_for_device(
        user=user,
        device_name=device_name,
        device_info=device_info
    )
    
    return Response({
        'token': token.key,
        'expires_at': token.expires_at.isoformat(),
        'device_name': token.device_name,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'display_name': getattr(user, 'display_name', None),
            'date_joined': user.date_joined.isoformat()
        }
    })


@api_view(['POST'])
@authentication_classes([EnhancedTokenAuthentication])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    """
    Refresh an enhanced authentication token.
    
    Takes the current token and returns a new one with extended expiration.
    The old token is invalidated in the process.
    """
    # Get the current token from authentication
    current_token = request.auth
    
    if not isinstance(current_token, EnhancedToken):
        return Response(
            {'error': 'Invalid token type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Store device info for new token
    device_name = current_token.device_name
    device_info = current_token.device_info
    user = current_token.user
    
    # Create new token with same device info
    new_token = EnhancedToken.objects.create_for_device(
        user=user,
        device_name=device_name,
        device_info=device_info
    )
    
    # Delete the old token
    current_token.delete()
    
    return Response({
        'token': new_token.key,
        'expires_at': new_token.expires_at.isoformat(),
        'device_name': new_token.device_name
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def register_user(request):
    """
    Register a new user account.
    
    Accepts username, password, and optional email, display_name, and device information.
    Returns the created user information and an enhanced token.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '').strip() or None
    display_name = request.data.get('display_name', '').strip()
    device_name = request.data.get('device_name', '')
    device_info = request.data.get('device_info', {})
    
    if not username:
        return Response(
            {'error': 'Username is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not password:
        return Response(
            {'error': 'Password is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate username length and characters
    if len(username.strip()) < 3:
        return Response(
            {'error': 'Username must be at least 3 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check username characters (only letters, numbers, underscores, hyphens)
    import re
    if not re.match(r'^[\w-]+$', username):
        return Response(
            {'error': 'Username can only contain letters, numbers, underscores, and hyphens'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate email format if provided
    if email:
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {'error': 'Invalid email format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Check for duplicate username
    if User.objects.filter(username__iexact=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check for duplicate email if provided
    if email and User.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Create user account
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            display_name=display_name
        )
        
        # Create enhanced token for the new user
        token = EnhancedToken.objects.create_for_device(
            user=user,
            device_name=device_name,
            device_info=device_info
        )
        
        # Prepare user data for response
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'display_name': user.display_name,
            'date_joined': user.date_joined.isoformat()
        }
        
        return Response({
            'user': user_data,
            'token': token.key,
            'expires_at': token.expires_at.isoformat(),
            'device_name': token.device_name
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        # Handle any validation errors from model validators
        if hasattr(e, 'message_dict'):
            # Django validation errors
            errors = []
            for field, messages in e.message_dict.items():
                errors.extend(messages)
            return Response(
                {'error': '; '.join(errors)},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif hasattr(e, 'messages'):
            # Django validation errors (list format)
            return Response(
                {'error': '; '.join(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # Generic error
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )