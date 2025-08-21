"""
Enhanced authentication backends for token-based authentication.

This module provides enhanced token authentication with expiration,
device tracking, and usage monitoring.
"""

from rest_framework import authentication, exceptions
from django.utils import timezone
from .models import EnhancedToken


class EnhancedTokenAuthentication(authentication.TokenAuthentication):
    """
    Enhanced token authentication with expiration and usage tracking.
    
    Extends DRF TokenAuthentication to support:
    - Token expiration validation
    - Last used timestamp tracking
    - Enhanced token model
    """
    
    model = EnhancedToken
    keyword = 'Token'
    
    def authenticate_credentials(self, key):
        """
        Authenticate the given credentials and return the user and token.
        
        Args:
            key: The token key to authenticate
            
        Returns:
            Tuple of (user, token) if authentication succeeds
            
        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')
        
        # Check if token has expired
        if token.is_expired:
            raise exceptions.AuthenticationFailed('Token has expired.')
        
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
        
        # Update last used timestamp
        token.update_last_used()
        
        return (token.user, token)