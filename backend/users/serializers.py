"""
DRF serializers for user models.
"""

from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """
    win_rate = serializers.ReadOnlyField()
    losses = serializers.ReadOnlyField()
    is_experienced = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'display_name',
            'games_played', 'games_won', 'win_rate', 'losses',
            'is_experienced', 'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'games_played', 'games_won']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True}
        }


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    """
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'display_name', 'password']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'display_name': {'required': False, 'allow_blank': True}
        }
    
    def create(self, validated_data):
        """Create user with optional password."""
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            # Set unusable password for guest users
            user.set_unusable_password()
        
        user.save()
        return user


class UserStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for user statistics.
    """
    win_rate = serializers.ReadOnlyField()
    losses = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['games_played', 'games_won', 'win_rate', 'losses']